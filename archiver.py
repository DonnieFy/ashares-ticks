# -*- coding: utf-8 -*-
"""
A股分时数据收集项目 — 数据归档工具

将超过指定天数的历史数据从本地 SSD 迁移到外部磁盘（如机械硬盘），
以节省本地存储空间。
"""

import logging
import os
import shutil
from datetime import datetime, timedelta

import config

logger = logging.getLogger(__name__)


def archive_old_data() -> int:
    """
    扫描数据目录，将超过阈值天数的子目录迁移到归档目录。

    Returns:
        迁移的目录数量
    """
    if not config.ARCHIVE_DIR:
        logger.debug("归档目录未配置 (ARCHIVE_DIR = None)，跳过归档")
        return 0

    if not os.path.exists(config.DATA_DIR):
        logger.debug("数据目录不存在，跳过归档")
        return 0

    # 确保归档目录存在
    os.makedirs(config.ARCHIVE_DIR, exist_ok=True)

    threshold_date = datetime.now().date() - timedelta(days=config.ARCHIVE_DAYS_THRESHOLD)
    archived_count = 0

    logger.info(
        f"开始归档检查: 阈值 {config.ARCHIVE_DAYS_THRESHOLD} 天, "
        f"截止日期 {threshold_date}, "
        f"目标目录 {config.ARCHIVE_DIR}"
    )

    for dirname in sorted(os.listdir(config.DATA_DIR)):
        src_path = os.path.join(config.DATA_DIR, dirname)
        if not os.path.isdir(src_path):
            continue

        # 尝试解析目录名为日期
        try:
            dir_date = datetime.strptime(dirname, "%Y-%m-%d").date()
        except ValueError:
            continue

        if dir_date >= threshold_date:
            continue

        # 需要归档
        dst_path = os.path.join(config.ARCHIVE_DIR, dirname)

        if os.path.exists(dst_path):
            logger.warning(f"归档目标已存在，跳过: {dst_path}")
            continue

        try:
            shutil.move(src_path, dst_path)
            archived_count += 1
            logger.info(f"  已归档: {dirname} -> {dst_path}")
        except Exception as e:
            logger.error(f"  归档失败 {dirname}: {e}", exc_info=True)

    if archived_count > 0:
        logger.info(f"归档完成，共迁移 {archived_count} 个目录")
    else:
        logger.info("没有需要归档的数据")

    return archived_count


def list_archive_status() -> None:
    """列出本地和归档目录中的数据概况"""
    print("=" * 60)
    print("数据存储概况")
    print("=" * 60)

    # 本地数据
    print(f"\n本地数据目录: {config.DATA_DIR}")
    if os.path.exists(config.DATA_DIR):
        dirs = sorted(
            d
            for d in os.listdir(config.DATA_DIR)
            if os.path.isdir(os.path.join(config.DATA_DIR, d))
        )
        total_size = 0
        for d in dirs:
            dir_path = os.path.join(config.DATA_DIR, d)
            size = sum(
                os.path.getsize(os.path.join(dir_path, f))
                for f in os.listdir(dir_path)
                if os.path.isfile(os.path.join(dir_path, f))
            )
            total_size += size
            print(f"  {d}  ({size / 1024 / 1024:.1f} MB)")
        print(f"  共 {len(dirs)} 天, {total_size / 1024 / 1024:.1f} MB")
    else:
        print("  (目录不存在)")

    # 归档数据
    print(f"\n归档数据目录: {config.ARCHIVE_DIR or '(未配置)'}")
    if config.ARCHIVE_DIR and os.path.exists(config.ARCHIVE_DIR):
        dirs = sorted(
            d
            for d in os.listdir(config.ARCHIVE_DIR)
            if os.path.isdir(os.path.join(config.ARCHIVE_DIR, d))
        )
        total_size = 0
        for d in dirs:
            dir_path = os.path.join(config.ARCHIVE_DIR, d)
            size = sum(
                os.path.getsize(os.path.join(dir_path, f))
                for f in os.listdir(dir_path)
                if os.path.isfile(os.path.join(dir_path, f))
            )
            total_size += size
        print(f"  共 {len(dirs)} 天, {total_size / 1024 / 1024:.1f} MB")

    print("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=config.LOG_FORMAT)

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        list_archive_status()
    else:
        archive_old_data()
