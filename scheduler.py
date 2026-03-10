# -*- coding: utf-8 -*-
"""
A股分时数据收集项目 — 时间调度与交易阶段管理
"""

import time
import logging
from enum import Enum
from datetime import datetime, time as dt_time

import config

logger = logging.getLogger(__name__)


class TradingPhase(Enum):
    """交易阶段枚举"""
    AUCTION_OPEN = "auction_open"     # 早盘竞价 09:15 - 09:25
    TRADING = "trading"               # 交易时间 09:30 - 11:30, 13:00 - 14:57
    AUCTION_CLOSE = "auction_close"   # 尾盘竞价 14:57 - 15:00
    MIDDAY_BREAK = "midday_break"     # 午间休市 11:30 - 13:00
    PRE_OPEN_GAP = "pre_open_gap"     # 竞价与开盘间隔 09:25 - 09:30
    CLOSED = "closed"                 # 休市（早盘前 / 收盘后）


# 时间边界定义
_AUCTION_OPEN_START = dt_time(9, 15, 0)
_AUCTION_OPEN_END = dt_time(9, 25, 0)
_PRE_OPEN_GAP_END = dt_time(9, 30, 0)
_MORNING_TRADING_END = dt_time(11, 30, 0)
_AFTERNOON_TRADING_START = dt_time(13, 0, 0)
_AUCTION_CLOSE_START = dt_time(14, 57, 0)
_AUCTION_CLOSE_END = dt_time(15, 0, 0)


def get_current_phase(now: datetime = None) -> TradingPhase:
    """根据当前时间返回所处的交易阶段"""
    if now is None:
        now = datetime.now()
    t = now.time()

    if t < _AUCTION_OPEN_START:
        return TradingPhase.CLOSED
    elif t < _AUCTION_OPEN_END:
        return TradingPhase.AUCTION_OPEN
    elif t < _PRE_OPEN_GAP_END:
        return TradingPhase.PRE_OPEN_GAP
    elif t < _MORNING_TRADING_END:
        return TradingPhase.TRADING
    elif t < _AFTERNOON_TRADING_START:
        return TradingPhase.MIDDAY_BREAK
    elif t < _AUCTION_CLOSE_START:
        return TradingPhase.TRADING
    elif t < _AUCTION_CLOSE_END:
        return TradingPhase.AUCTION_CLOSE
    else:
        return TradingPhase.CLOSED


def get_phase_file_suffix(phase: TradingPhase) -> str:
    """获取阶段对应的文件后缀"""
    mapping = {
        TradingPhase.AUCTION_OPEN: config.PHASE_AUCTION_OPEN,
        TradingPhase.TRADING: config.PHASE_TRADING,
        TradingPhase.AUCTION_CLOSE: config.PHASE_AUCTION_CLOSE,
    }
    return mapping.get(phase)


def get_tick_interval(phase: TradingPhase) -> float:
    """获取阶段的数据刷新间隔（秒）"""
    if phase in (TradingPhase.AUCTION_OPEN, TradingPhase.AUCTION_CLOSE):
        return config.TICK_INTERVAL_AUCTION
    elif phase == TradingPhase.TRADING:
        return config.TICK_INTERVAL_TRADING
    return 1.0  # 非交易阶段默认


def calc_seconds_to_next_tick(phase: TradingPhase) -> float:
    """
    计算距离下一个数据 tick 对齐点的等待时间（秒）。

    交易时间：对齐到 3 秒边界（0, 3, 6, 9, ...）
    竞价时间：对齐到 9 秒边界（0, 9, 18, 27, ...）

    返回值为需要等待的秒数，范围 (0, interval]
    """
    now = datetime.now()
    interval = get_tick_interval(phase)
    interval_int = int(interval)

    # 计算当前秒数到下一个对齐点的距离
    seconds_into_cycle = now.second % interval_int
    if seconds_into_cycle == 0:
        # 恰好在边界上，等待一个完整周期减去已过的微秒
        wait = interval - now.microsecond / 1_000_000
    else:
        wait = (interval_int - seconds_into_cycle) - now.microsecond / 1_000_000

    # 确保至少等待 API_MIN_INTERVAL
    return max(wait, config.API_MIN_INTERVAL)


def wait_for_market_open() -> None:
    """等待到早盘竞价开始时间 (09:15)"""
    now = datetime.now()
    target = now.replace(hour=9, minute=15, second=0, microsecond=0)

    if now >= target:
        return

    wait_seconds = (target - now).total_seconds()
    logger.info(f"等待开盘，距离 09:15 还有 {wait_seconds:.0f} 秒")
    time.sleep(wait_seconds)


def wait_for_next_phase(current_phase: TradingPhase) -> TradingPhase:
    """
    等待直到进入下一个数据采集阶段。
    返回新的阶段。
    """
    while True:
        time.sleep(0.05)
        new_phase = get_current_phase()
        if new_phase != current_phase:
            return new_phase


def is_data_phase(phase: TradingPhase) -> bool:
    """判断当前阶段是否需要采集数据"""
    return phase in (
        TradingPhase.AUCTION_OPEN,
        TradingPhase.TRADING,
        TradingPhase.AUCTION_CLOSE,
    )


def is_market_ended(phase: TradingPhase) -> bool:
    """判断是否已收盘"""
    return phase == TradingPhase.CLOSED and datetime.now().time() >= _AUCTION_CLOSE_END
