# -*- coding: utf-8 -*-
"""
A股分时数据收集项目 — 配置文件
"""

import os

# ============================================================
# 目录配置
# ============================================================

# 数据输出目录（相对于项目根目录）
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# 归档目录 — 设置为外部磁盘路径以迁移旧数据，节省 SSD 空间
# 例如: ARCHIVE_DIR = "E:/ashares-archive"
# 设置为 None 则不启用归档
ARCHIVE_DIR = None

# 超过多少天的数据会被归档迁移
ARCHIVE_DAYS_THRESHOLD = 30

# ============================================================
# API 配置
# ============================================================

# API 最小请求间隔（秒）
API_MIN_INTERVAL = 0.3

# API 请求最大重试次数
API_MAX_RETRIES = 5

# ============================================================
# 交易阶段配置
# ============================================================

# 文件后缀定义
PHASE_AUCTION_OPEN = "auction_open"
PHASE_TRADING = "trading"
PHASE_AUCTION_CLOSE = "auction_close"

# 数据刷新间隔（秒）
TICK_INTERVAL_AUCTION = 9   # 竞价阶段 9 秒一更新
TICK_INTERVAL_TRADING = 3   # 交易阶段 3 秒一更新

# ============================================================
# CSV 列定义
# ============================================================

# CSV 文件中各列的顺序（不写入列头，此处定义供参考和程序使用）
# 第一列为 code（股票代码，含 sh/sz 前缀）
CSV_COLUMNS = [
    "code",
    "name",
    "open",
    "close",
    "now",
    "high",
    "low",
    "buy",
    "sell",
    "turnover",
    "volume",
    "bid1_volume",
    "bid1",
    "bid2_volume",
    "bid2",
    "bid3_volume",
    "bid3",
    "bid4_volume",
    "bid4",
    "bid5_volume",
    "bid5",
    "ask1_volume",
    "ask1",
    "ask2_volume",
    "ask2",
    "ask3_volume",
    "ask3",
    "ask4_volume",
    "ask4",
    "ask5_volume",
    "ask5",
    "date",
    "time",
]

# snapshot 中的字段（不含 code，code 是 dict 的 key）
SNAPSHOT_FIELDS = CSV_COLUMNS[1:]

# ============================================================
# 日志配置
# ============================================================

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
