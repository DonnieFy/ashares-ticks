# -*- coding: utf-8 -*-
"""
A股分时数据收集项目 — 股票列表管理工具
"""

import json
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)


def _get_stock_codes_path() -> str:
    """获取 easyquotation 的 stock_codes.conf 文件路径"""
    try:
        import easyquotation
        pkg_dir = os.path.dirname(easyquotation.__file__)
        return os.path.join(pkg_dir, "stock_codes.conf")
    except ImportError:
        logger.error("easyquotation 未安装")
        raise


def update_stock_codes() -> list[str]:
    """
    从网络获取最新的 A 股全部股票列表，并更新 easyquotation 的配置文件。

    数据源: http://www.shdjt.com/js/lib/astock.js
    这是 easyquotation 内置的同一个数据源。

    Returns:
        更新后的股票代码列表
    """
    url = "http://www.shdjt.com/js/lib/astock.js"
    logger.info(f"正在从 {url} 获取最新股票列表...")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        stock_codes = re.findall(r"~([a-z0-9]*)`", response.text)

        if not stock_codes:
            logger.warning("未能解析到股票代码，保持现有列表不变")
            return get_current_stock_codes()

        conf_path = _get_stock_codes_path()
        with open(conf_path, "w") as f:
            f.write(json.dumps({"stock": stock_codes}))

        logger.info(f"股票列表已更新，共 {len(stock_codes)} 只股票，写入 {conf_path}")
        return stock_codes

    except Exception as e:
        logger.warning(f"股票列表更新失败: {e}，将使用现有列表")
        return get_current_stock_codes()


def get_current_stock_codes() -> list[str]:
    """读取当前的股票代码列表"""
    conf_path = _get_stock_codes_path()
    with open(conf_path) as f:
        return json.load(f)["stock"]


def get_stock_count() -> int:
    """返回当前股票列表中的股票数量"""
    return len(get_current_stock_codes())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    codes = update_stock_codes()
    print(f"共 {len(codes)} 只股票")
