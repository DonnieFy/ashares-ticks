# A股分时数据收集项目

自动化收集 A 股全市场分时数据。在每个交易日运行，通过新浪行情 API（easyquotation）定时获取所有股票的实时快照，按交易阶段分别记录为 CSV 文件，收盘后压缩为 `.csv.gz` 格式。

## 功能特性

- **三阶段数据采集**：早盘竞价（9:15-9:25）、连续交易（9:30-11:30, 13:00-14:57）、尾盘竞价（14:57-15:00）
- **读写分离架构**：采集线程与写入线程独立运行，确保数据不丢失
- **智能去重**：自动判断新数据，避免重复写入
- **原子写入**：先写临时文件再追加到主文件，支持外部文件监听
- **数据归档**：支持将旧数据迁移到外部磁盘，节省 SSD 空间
- **自动更新股票列表**：每日启动时自动获取最新的全市场股票列表

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试（可在非交易时间执行）
python test_dry_run.py

# 启动数据采集（需在交易日运行）
python main.py
```

## 项目结构

```
├── config.py          # 配置文件
├── collector.py       # 数据采集引擎（读取线程）
├── writer.py          # 数据写入服务（写入线程）
├── scheduler.py       # 时间调度与交易阶段管理
├── stock_list.py      # 股票列表管理工具
├── archiver.py        # 数据归档（迁移旧数据到外部磁盘）
├── main.py            # 主入口
├── test_dry_run.py    # 功能测试脚本
├── docs/columns.md    # CSV 列头格式文档
└── data/              # 数据输出目录
```

## 数据格式

CSV 文件不包含列头，共 33 列。详细说明见 [docs/columns.md](docs/columns.md)。

每日数据存储在 `data/{date}/` 目录下：
- `{date}_auction_open.csv.gz` — 早盘竞价
- `{date}_trading.csv.gz` — 连续交易
- `{date}_auction_close.csv.gz` — 尾盘竞价

## 配置说明

编辑 `config.py` 可调整以下配置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DATA_DIR` | `./data` | 数据输出目录 |
| `ARCHIVE_DIR` | `None` | 归档目录（外部磁盘路径） |
| `ARCHIVE_DAYS_THRESHOLD` | `30` | 归档天数阈值 |
| `API_MIN_INTERVAL` | `0.3` | API 最小请求间隔（秒） |

## 工具命令

```bash
# 独立更新股票列表
python stock_list.py

# 独立执行归档
python archiver.py

# 查看数据存储概况
python archiver.py status
```