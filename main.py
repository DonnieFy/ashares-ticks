# -*- coding: utf-8 -*-
"""
A股分时数据收集项目 — 主入口

启动流程：
1. 初始化日志
2. 更新股票列表
3. 执行数据归档
4. 启动写入线程
5. 在主线程运行数据采集引擎
6. 收盘后压缩数据文件
"""

import logging
import os
import sys
import threading
from datetime import datetime
from queue import Queue

import config
import archiver
import stock_list
from collector import DataCollector
from writer import DataWriter

logger = logging.getLogger("ashares_ticks")


def setup_logging() -> None:
    """初始化日志系统"""
    os.makedirs(config.LOG_DIR, exist_ok=True)

    date_string = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(config.LOG_DIR, f"{date_string}.log")

    # 根 logger 配置
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 文件 handler — 记录所有级别
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(config.LOG_FORMAT, datefmt=config.LOG_DATE_FORMAT)
    )

    # 控制台 handler — 只记录 INFO 及以上
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter(config.LOG_FORMAT, datefmt=config.LOG_DATE_FORMAT)
    )

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def main() -> None:
    """主入口"""
    setup_logging()

    date_string = datetime.now().strftime("%Y-%m-%d")
    logger.info("=" * 60)
    logger.info(f"A股分时数据收集 — {date_string}")
    logger.info("=" * 60)

    # 1. 更新股票列表
    logger.info("步骤 1: 更新股票列表")
    try:
        codes = stock_list.update_stock_codes()
        logger.info(f"股票列表就绪，共 {len(codes)} 只股票")
    except Exception as e:
        logger.error(f"股票列表更新失败: {e}", exc_info=True)
        logger.info("将使用现有股票列表继续运行")

    # 2. 数据归档
    logger.info("步骤 2: 数据归档检查")
    try:
        archiver.archive_old_data()
    except Exception as e:
        logger.error(f"归档过程出错: {e}", exc_info=True)

    # 3. 创建写入队列和写入线程
    logger.info("步骤 3: 启动写入服务")
    write_queue = Queue()
    data_writer = DataWriter(write_queue, date_string)

    writer_thread = threading.Thread(
        target=data_writer.start,
        name="DataWriterThread",
        daemon=True,
    )
    writer_thread.start()

    # 4. 主线程运行数据采集引擎
    logger.info("步骤 4: 启动数据采集引擎")
    collector = DataCollector(write_queue, date_string)

    try:
        collector.start()
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在停止...")
        collector.stop()

    # 5. 发送退出信号给写入线程
    logger.info("步骤 5: 等待写入线程完成")
    write_queue.put(None)  # 毒丸信号
    writer_thread.join(timeout=30)

    if writer_thread.is_alive():
        logger.warning("写入线程在 30 秒内未完成退出")

    # 6. 压缩当日文件
    logger.info("步骤 6: 压缩当日数据文件")
    data_writer.compress_daily_files()

    logger.info("=" * 60)
    logger.info("当日数据收集完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
