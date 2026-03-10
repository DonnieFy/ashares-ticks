# -*- coding: utf-8 -*-
"""
A股分时数据收集项目 — 功能测试脚本

可在非交易时间运行，验证各模块的核心逻辑。
运行方式: python test_dry_run.py
"""

import csv
import gzip
import os
import shutil
import sys
import tempfile
import traceback
from datetime import datetime, time as dt_time
from queue import Queue

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import scheduler
from scheduler import TradingPhase
from writer import DataWriter


class TestResult:
    """简单的测试结果收集器"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name: str):
        self.passed += 1
        print(f"  ✅ {name}")

    def fail(self, name: str, detail: str = ""):
        self.failed += 1
        self.errors.append((name, detail))
        print(f"  ❌ {name}: {detail}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'=' * 50}")
        print(f"测试结果: {self.passed}/{total} 通过")
        if self.errors:
            print("\n失败项:")
            for name, detail in self.errors:
                print(f"  - {name}: {detail}")
        print(f"{'=' * 50}")
        return self.failed == 0


def test_scheduler(result: TestResult):
    """测试调度器的时间阶段判断"""
    print("\n📅 测试调度器 (scheduler.py)")

    # 测试各时间点的阶段判断
    test_cases = [
        (dt_time(8, 0, 0), TradingPhase.CLOSED, "早盘前"),
        (dt_time(9, 14, 59), TradingPhase.CLOSED, "竞价前1秒"),
        (dt_time(9, 15, 0), TradingPhase.AUCTION_OPEN, "竞价开始"),
        (dt_time(9, 20, 0), TradingPhase.AUCTION_OPEN, "竞价进行中"),
        (dt_time(9, 24, 59), TradingPhase.AUCTION_OPEN, "竞价最后1秒"),
        (dt_time(9, 25, 0), TradingPhase.PRE_OPEN_GAP, "竞价-开盘间隔"),
        (dt_time(9, 30, 0), TradingPhase.TRADING, "开盘"),
        (dt_time(10, 30, 0), TradingPhase.TRADING, "上午交易中"),
        (dt_time(11, 29, 59), TradingPhase.TRADING, "上午收盘前1秒"),
        (dt_time(11, 30, 0), TradingPhase.MIDDAY_BREAK, "午休开始"),
        (dt_time(12, 30, 0), TradingPhase.MIDDAY_BREAK, "午休中"),
        (dt_time(13, 0, 0), TradingPhase.TRADING, "下午开盘"),
        (dt_time(14, 30, 0), TradingPhase.TRADING, "下午交易中"),
        (dt_time(14, 56, 59), TradingPhase.TRADING, "尾盘竞价前1秒"),
        (dt_time(14, 57, 0), TradingPhase.AUCTION_CLOSE, "尾盘竞价开始"),
        (dt_time(14, 59, 59), TradingPhase.AUCTION_CLOSE, "尾盘竞价最后1秒"),
        (dt_time(15, 0, 0), TradingPhase.CLOSED, "收盘"),
        (dt_time(20, 0, 0), TradingPhase.CLOSED, "晚间"),
    ]

    for t, expected, desc in test_cases:
        now = datetime.now().replace(
            hour=t.hour, minute=t.minute, second=t.second, microsecond=0
        )
        actual = scheduler.get_current_phase(now)
        if actual == expected:
            result.ok(f"时间 {t.strftime('%H:%M:%S')} -> {expected.value} ({desc})")
        else:
            result.fail(
                f"时间 {t.strftime('%H:%M:%S')} ({desc})",
                f"期望 {expected.value}, 实际 {actual.value}",
            )

    # 测试 tick 间隔
    auction_interval = scheduler.get_tick_interval(TradingPhase.AUCTION_OPEN)
    if auction_interval == 9:
        result.ok(f"竞价间隔 = {auction_interval}s")
    else:
        result.fail("竞价间隔", f"期望 9, 实际 {auction_interval}")

    trading_interval = scheduler.get_tick_interval(TradingPhase.TRADING)
    if trading_interval == 3:
        result.ok(f"交易间隔 = {trading_interval}s")
    else:
        result.fail("交易间隔", f"期望 3, 实际 {trading_interval}")

    # 测试文件后缀
    for phase, expected_suffix in [
        (TradingPhase.AUCTION_OPEN, "auction_open"),
        (TradingPhase.TRADING, "trading"),
        (TradingPhase.AUCTION_CLOSE, "auction_close"),
    ]:
        suffix = scheduler.get_phase_file_suffix(phase)
        if suffix == expected_suffix:
            result.ok(f"{phase.value} 文件后缀 = {suffix}")
        else:
            result.fail(f"{phase.value} 文件后缀", f"期望 {expected_suffix}, 实际 {suffix}")


def test_writer(result: TestResult):
    """测试写入 -> 压缩 -> 读取流程"""
    print("\n📝 测试写入服务 (writer.py)")

    # 使用临时目录
    original_data_dir = config.DATA_DIR
    tmp_dir = tempfile.mkdtemp(prefix="ashares_test_")

    try:
        config.DATA_DIR = tmp_dir
        date_string = "2026-01-01"

        # 创建写入队列和 writer
        write_queue = Queue()
        writer = DataWriter(write_queue, date_string)

        # 模拟两帧数据
        mock_snapshot_1 = {
            "sh600000": {
                "name": "浦发银行",
                "open": 9.56,
                "close": 9.60,
                "now": 9.78,
                "high": 9.81,
                "low": 9.56,
                "buy": 9.77,
                "sell": 9.78,
                "turnover": 50000000,
                "volume": 490000000.0,
                "bid1_volume": 100000,
                "bid1": 9.77,
                "bid2_volume": 80000,
                "bid2": 9.76,
                "bid3_volume": 60000,
                "bid3": 9.75,
                "bid4_volume": 50000,
                "bid4": 9.74,
                "bid5_volume": 40000,
                "bid5": 9.73,
                "ask1_volume": 90000,
                "ask1": 9.78,
                "ask2_volume": 70000,
                "ask2": 9.79,
                "ask3_volume": 60000,
                "ask3": 9.80,
                "ask4_volume": 50000,
                "ask4": 9.81,
                "ask5_volume": 40000,
                "ask5": 9.82,
                "date": "2026-01-01",
                "time": "09:30:00",
            },
            "sz000001": {
                "name": "平安银行",
                "open": 12.00,
                "close": 12.10,
                "now": 12.05,
                "high": 12.15,
                "low": 11.95,
                "buy": 12.04,
                "sell": 12.05,
                "turnover": 30000000,
                "volume": 360000000.0,
                "bid1_volume": 50000,
                "bid1": 12.04,
                "bid2_volume": 40000,
                "bid2": 12.03,
                "bid3_volume": 30000,
                "bid3": 12.02,
                "bid4_volume": 25000,
                "bid4": 12.01,
                "bid5_volume": 20000,
                "bid5": 12.00,
                "ask1_volume": 45000,
                "ask1": 12.05,
                "ask2_volume": 35000,
                "ask2": 12.06,
                "ask3_volume": 25000,
                "ask3": 12.07,
                "ask4_volume": 20000,
                "ask4": 12.08,
                "ask5_volume": 15000,
                "ask5": 12.09,
                "date": "2026-01-01",
                "time": "09:30:00",
            },
        }

        mock_snapshot_2 = {
            "sh600000": {**mock_snapshot_1["sh600000"], "now": 9.80, "time": "09:30:03"},
            "sz000001": {**mock_snapshot_1["sz000001"], "now": 12.08, "time": "09:30:03"},
        }

        # 写入两帧
        writer._write_snapshot("trading", mock_snapshot_1)
        writer._write_snapshot("trading", mock_snapshot_2)

        # 检查 CSV 文件
        csv_file = os.path.join(writer.data_dir, f"{date_string}_trading.csv")
        if os.path.exists(csv_file):
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)

            if len(rows) == 4:  # 2 帧 × 2 只股票
                result.ok(f"CSV 文件行数正确: {len(rows)} 行")
            else:
                result.fail("CSV 文件行数", f"期望 4, 实际 {len(rows)}")

            # 验证第一行内容
            if rows[0][0] == "sh600000" and rows[0][1] == "浦发银行":
                result.ok("CSV 数据内容正确")
            else:
                result.fail("CSV 数据内容", f"首行: {rows[0][:3]}")
        else:
            result.fail("CSV 文件", "文件不存在")

        # 压缩测试
        writer.compress_daily_files()

        gz_file = csv_file + ".gz"
        if os.path.exists(gz_file) and not os.path.exists(csv_file):
            result.ok("压缩成功，原始 CSV 已删除")
        else:
            result.fail("压缩", f"gz存在={os.path.exists(gz_file)}, csv存在={os.path.exists(csv_file)}")

        # pandas 读取测试
        try:
            import pandas as pd

            df = pd.read_csv(
                gz_file,
                names=config.CSV_COLUMNS,
                header=None,
                compression="gzip",
            )
            if len(df) == 4 and "code" in df.columns:
                result.ok(f"pandas 读取压缩文件成功: {len(df)} 行, {len(df.columns)} 列")
            else:
                result.fail("pandas 读取", f"{len(df)} 行, {len(df.columns)} 列")

            # 验证数据
            sh600000_rows = df[df["code"] == "sh600000"]
            if len(sh600000_rows) == 2:
                result.ok("按股票代码过滤正确")
            else:
                result.fail("股票代码过滤", f"期望 2 行, 实际 {len(sh600000_rows)}")

        except ImportError:
            result.fail("pandas 读取", "pandas 未安装")

    finally:
        config.DATA_DIR = original_data_dir
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_archiver(result: TestResult):
    """测试归档功能"""
    print("\n📦 测试归档工具 (archiver.py)")

    import archiver

    original_data_dir = config.DATA_DIR
    original_archive_dir = config.ARCHIVE_DIR
    original_threshold = config.ARCHIVE_DAYS_THRESHOLD

    tmp_data = tempfile.mkdtemp(prefix="ashares_data_")
    tmp_archive = tempfile.mkdtemp(prefix="ashares_archive_")

    try:
        config.DATA_DIR = tmp_data
        config.ARCHIVE_DIR = tmp_archive
        config.ARCHIVE_DAYS_THRESHOLD = 7

        # 创建模拟数据目录
        old_date = "2025-01-01"
        recent_date = datetime.now().strftime("%Y-%m-%d")

        old_dir = os.path.join(tmp_data, old_date)
        recent_dir = os.path.join(tmp_data, recent_date)
        os.makedirs(old_dir)
        os.makedirs(recent_dir)

        # 写入模拟文件
        with open(os.path.join(old_dir, "test.csv.gz"), "w") as f:
            f.write("test data")
        with open(os.path.join(recent_dir, "test.csv.gz"), "w") as f:
            f.write("test data")

        # 执行归档
        count = archiver.archive_old_data()

        # 验证
        if count == 1:
            result.ok(f"归档数量正确: {count}")
        else:
            result.fail("归档数量", f"期望 1, 实际 {count}")

        if os.path.exists(os.path.join(tmp_archive, old_date)):
            result.ok("旧数据已迁移到归档目录")
        else:
            result.fail("旧数据迁移", "归档目录中未找到")

        if not os.path.exists(old_dir):
            result.ok("原目录已删除")
        else:
            result.fail("原目录删除", "原目录仍存在")

        if os.path.exists(recent_dir):
            result.ok("近期数据未被归档")
        else:
            result.fail("近期数据", "近期数据被误归档")

        # 测试未配置归档目录时跳过
        config.ARCHIVE_DIR = None
        count = archiver.archive_old_data()
        if count == 0:
            result.ok("ARCHIVE_DIR=None 时正确跳过")
        else:
            result.fail("跳过归档", f"期望 0, 实际 {count}")

    finally:
        config.DATA_DIR = original_data_dir
        config.ARCHIVE_DIR = original_archive_dir
        config.ARCHIVE_DAYS_THRESHOLD = original_threshold
        shutil.rmtree(tmp_data, ignore_errors=True)
        shutil.rmtree(tmp_archive, ignore_errors=True)


def test_stock_list(result: TestResult):
    """测试股票列表功能"""
    print("\n📊 测试股票列表 (stock_list.py)")

    import stock_list

    try:
        count = stock_list.get_stock_count()
        if count > 0:
            result.ok(f"当前股票列表: {count} 只")
        else:
            result.fail("股票列表", "列表为空")
    except Exception as e:
        result.fail("读取股票列表", str(e))

    # 测试更新（实际网络请求）
    try:
        codes = stock_list.update_stock_codes()
        if len(codes) > 0:
            result.ok(f"股票列表更新成功: {len(codes)} 只")
        else:
            result.fail("股票列表更新", "更新后列表为空")
    except Exception as e:
        result.fail("股票列表更新", str(e))


def main():
    print("=" * 50)
    print("A股分时数据收集 — 功能测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    import logging
    logging.basicConfig(level=logging.WARNING)

    result = TestResult()

    try:
        test_scheduler(result)
    except Exception as e:
        result.fail("调度器测试异常", traceback.format_exc())

    try:
        test_writer(result)
    except Exception as e:
        result.fail("写入测试异常", traceback.format_exc())

    try:
        test_archiver(result)
    except Exception as e:
        result.fail("归档测试异常", traceback.format_exc())

    try:
        test_stock_list(result)
    except Exception as e:
        result.fail("股票列表测试异常", traceback.format_exc())

    success = result.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
