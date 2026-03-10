# -*- coding: utf-8 -*-
"""
A股分时数据收集项目 — 数据写入服务（写入线程）

设计要点：
- 从 Queue 中读取采集到的快照数据
- 先写入临时 .csv 文件，完成后追加到主 .csv 文件
- 支持外部文件监听：监听方在主文件变化后读取即可获取完整的新增数据
- 收盘后将 .csv 压缩为 .csv.gz 并删除原始 .csv
"""

import csv
import gzip
import io
import logging
import os
import shutil
from queue import Queue

import config
from scheduler import TradingPhase

logger = logging.getLogger(__name__)


class DataWriter:
    """数据写入服务 — 运行在独立的写入线程"""

    def __init__(self, write_queue: Queue, date_string: str):
        self.write_queue = write_queue
        self.date_string = date_string
        self.data_dir = os.path.join(config.DATA_DIR, date_string)
        self.write_count = {
            config.PHASE_AUCTION_OPEN: 0,
            config.PHASE_TRADING: 0,
            config.PHASE_AUCTION_CLOSE: 0,
        }

        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)

    def start(self) -> None:
        """持续从队列取数据并写入文件，直到收到退出信号"""
        logger.info("写入线程已启动")

        while True:
            try:
                item = self.write_queue.get()

                # 毒丸信号 — 退出
                if item is None:
                    logger.info("写入线程收到退出信号")
                    break

                phase_suffix, snapshot_dict = item
                self._write_snapshot(phase_suffix, snapshot_dict)
                self.write_queue.task_done()

            except Exception as e:
                logger.error(f"写入线程异常: {e}", exc_info=True)

        # 退出前打印统计
        for phase, count in self.write_count.items():
            logger.info(f"  [{phase}] 共写入 {count} 帧数据")

    def _write_snapshot(self, phase_suffix: str, snapshot: dict) -> None:
        """
        将一帧快照数据写入文件。

        流程：
        1. 将 snapshot dict 转为 CSV 行（不含列头）
        2. 写入临时文件 {phase}.tmp.csv
        3. 将临时文件内容追加到主文件 {date}_{phase}.csv
        4. 删除临时文件
        """
        main_file = os.path.join(
            self.data_dir, f"{self.date_string}_{phase_suffix}.csv"
        )
        tmp_file = os.path.join(self.data_dir, f"{phase_suffix}.tmp.csv")

        try:
            # 1. 写入临时文件
            with open(tmp_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for code, data in snapshot.items():
                    row = [code]
                    for field in config.SNAPSHOT_FIELDS:
                        row.append(data.get(field, ""))
                    writer.writerow(row)

            # 2. 追加到主文件
            with open(tmp_file, "r", encoding="utf-8") as src:
                content = src.read()

            with open(main_file, "a", encoding="utf-8") as dst:
                dst.write(content)

            # 3. 删除临时文件
            os.remove(tmp_file)

            self.write_count[phase_suffix] = self.write_count.get(phase_suffix, 0) + 1
            stock_count = len(snapshot)
            logger.debug(
                f"[{phase_suffix}] 第 {self.write_count[phase_suffix]} 帧写入完成，"
                f"{stock_count} 只股票"
            )

        except Exception as e:
            logger.error(f"写入文件失败: {e}", exc_info=True)

    def compress_daily_files(self) -> None:
        """
        收盘后将当日所有 .csv 文件压缩为 .csv.gz 并删除原始 .csv。
        """
        logger.info("开始压缩当日数据文件...")
        compressed = 0

        for filename in os.listdir(self.data_dir):
            if filename.endswith(".csv") and not filename.endswith(".tmp.csv"):
                csv_path = os.path.join(self.data_dir, filename)
                gz_path = csv_path + ".gz"

                try:
                    with open(csv_path, "rb") as f_in:
                        with gzip.open(gz_path, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)

                    # 验证压缩文件可读
                    with gzip.open(gz_path, "rt", encoding="utf-8") as f:
                        first_line = f.readline()
                        if not first_line:
                            logger.warning(f"压缩文件为空: {gz_path}")

                    os.remove(csv_path)
                    compressed += 1
                    csv_size = os.path.getsize(gz_path)
                    logger.info(
                        f"  已压缩: {filename} -> {filename}.gz ({csv_size} bytes)"
                    )

                except Exception as e:
                    logger.error(f"压缩文件失败 {filename}: {e}", exc_info=True)

        logger.info(f"压缩完成，共 {compressed} 个文件")
