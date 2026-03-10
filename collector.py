# -*- coding: utf-8 -*-
"""
A股分时数据收集项目 — 数据采集引擎（读取线程）

设计要点：
- 运行在主线程（或独立线程），负责定时调用 API 获取全市场快照
- 所有异常都在内部捕获，绝对不中断采集循环
- 通过比较 time 字段判断是否是新数据
- 采集到新数据后放入 write_queue，由写入线程异步处理
"""

import logging
import time
from datetime import datetime
from queue import Queue

import easyquotation

import config
import scheduler
from scheduler import TradingPhase

logger = logging.getLogger(__name__)


class DataCollector:
    """数据采集引擎"""

    def __init__(self, write_queue: Queue, date_string: str):
        self.write_queue = write_queue
        self.date_string = date_string
        self.last_tick_time = None       # 上次快照的 time 字段值
        self.current_phase = None        # 当前交易阶段
        self.running = False

        # 统计
        self.total_fetches = 0           # 总请求次数
        self.total_new_ticks = 0         # 总新数据帧数
        self.total_duplicate_skips = 0   # 总重复跳过次数

    def start(self) -> None:
        """
        主采集循环。

        流程：
        1. 等待开盘
        2. 进入循环：
           - 判断当前阶段
           - 如果是数据采集阶段，获取快照并判重
           - 如果是间歇阶段（午休、竞价间隔），等待
           - 如果收盘，退出
        """
        self.running = True
        logger.info("数据采集引擎已启动")

        # 初始化 easyquotation
        try:
            quotation = easyquotation.use("sina")
            logger.info(f"easyquotation 初始化完成，股票列表共 {len(quotation.stock_list)} 批")
        except Exception as e:
            logger.error(f"easyquotation 初始化失败: {e}", exc_info=True)
            return

        # 等待开盘
        scheduler.wait_for_market_open()

        while self.running:
            try:
                phase = scheduler.get_current_phase()

                # 收盘 — 退出
                if scheduler.is_market_ended(phase):
                    logger.info("已收盘，采集引擎退出")
                    break

                # 阶段切换
                if phase != self.current_phase:
                    old_phase = self.current_phase
                    self.current_phase = phase
                    self.last_tick_time = None  # 重置去重标记
                    logger.info(
                        f"阶段切换: {old_phase} -> {phase.value if phase else 'None'}"
                    )

                # 数据采集阶段
                if scheduler.is_data_phase(phase):
                    self._collect_tick(quotation, phase)
                else:
                    # 非数据阶段（午休、竞价间隔），等待到下一阶段
                    logger.debug(f"当前阶段 {phase.value}，等待下一数据阶段...")
                    new_phase = scheduler.wait_for_next_phase(phase)
                    continue

            except Exception as e:
                # 采集循环永远不应该因为异常而退出
                logger.error(f"采集循环异常（已恢复）: {e}", exc_info=True)
                time.sleep(config.API_MIN_INTERVAL)

        # 采集结束统计
        logger.info(
            f"采集统计: 总请求 {self.total_fetches} 次, "
            f"新数据 {self.total_new_ticks} 帧, "
            f"重复跳过 {self.total_duplicate_skips} 次"
        )

    def stop(self) -> None:
        """停止采集"""
        self.running = False
        logger.info("采集引擎停止中...")

    def _collect_tick(self, quotation, phase: TradingPhase) -> None:
        """
        执行一次数据采集 tick。

        策略：
        - 先判断是否到达对齐时间点，获取快照
        - 如果是新数据，放入写入队列
        - 如果不是新数据，短暂等待后再次尝试（心跳查询）
        - 最终等待到下一个 tick 对齐点
        """
        phase_suffix = scheduler.get_phase_file_suffix(phase)
        tick_interval = scheduler.get_tick_interval(phase)

        # 获取快照
        snapshot = self._fetch_snapshot(quotation)
        if snapshot is None:
            time.sleep(config.API_MIN_INTERVAL)
            return

        # 判断是否是新数据
        current_time = self._get_snapshot_time(snapshot)
        if current_time and current_time != self.last_tick_time:
            # 新数据
            self.last_tick_time = current_time
            self.total_new_ticks += 1

            # 过滤掉非当日数据
            filtered = {
                code: data
                for code, data in snapshot.items()
                if data.get("date") == self.date_string
            }

            if filtered:
                self.write_queue.put((phase_suffix, filtered))
                logger.info(
                    f"[{phase_suffix}] 新数据 @ {current_time}, "
                    f"{len(filtered)} 只股票, "
                    f"帧 #{self.total_new_ticks}"
                )
            else:
                logger.warning(f"[{phase_suffix}] 新数据为空（非当日）@ {current_time}")
        else:
            self.total_duplicate_skips += 1
            logger.debug(
                f"[{phase_suffix}] 重复数据跳过 @ {current_time}"
            )

        # 心跳查询策略：
        # 如果距下一个 tick 对齐点还有较长时间，在中间进行查询
        # 确保新数据出现时能尽快捕获
        wait_time = scheduler.calc_seconds_to_next_tick(phase)

        if wait_time > config.API_MIN_INTERVAL * 3:
            # 先等待一半时间
            half_wait = wait_time / 2
            time.sleep(max(half_wait, config.API_MIN_INTERVAL))

            # 心跳查询
            heartbeat = self._fetch_snapshot(quotation)
            if heartbeat:
                hb_time = self._get_snapshot_time(heartbeat)
                if hb_time and hb_time != self.last_tick_time:
                    # 心跳发现新数据
                    self.last_tick_time = hb_time
                    self.total_new_ticks += 1
                    filtered = {
                        code: data
                        for code, data in heartbeat.items()
                        if data.get("date") == self.date_string
                    }
                    if filtered:
                        self.write_queue.put((phase_suffix, filtered))
                        logger.info(
                            f"[{phase_suffix}] 心跳捕获新数据 @ {hb_time}, "
                            f"{len(filtered)} 只股票"
                        )

            # 等待剩余时间
            remaining = scheduler.calc_seconds_to_next_tick(phase)
            if remaining > 0:
                time.sleep(remaining)
        else:
            time.sleep(wait_time)

    def _fetch_snapshot(self, quotation) -> dict | None:
        """
        获取全市场快照，带重试和异常保护。

        返回: snapshot dict 或 None（失败时）
        """
        for retry in range(config.API_MAX_RETRIES):
            try:
                self.total_fetches += 1
                snapshot = quotation.market_snapshot(prefix=True)
                return snapshot

            except Exception as e:
                logger.warning(
                    f"API 请求失败 (重试 {retry + 1}/{config.API_MAX_RETRIES}): {e}"
                )
                time.sleep(config.API_MIN_INTERVAL)

        logger.error("API 请求已达到最大重试次数")
        return None

    @staticmethod
    def _get_snapshot_time(snapshot: dict) -> str | None:
        """从快照中提取 time 字段（取第一只股票的 time 值）"""
        if not snapshot:
            return None
        first_code = next(iter(snapshot))
        return snapshot[first_code].get("time")
