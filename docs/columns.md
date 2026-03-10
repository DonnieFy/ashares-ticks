# CSV 列头格式说明

本项目生成的 `.csv` / `.csv.gz` 数据文件**不包含列头**，以节省存储空间并简化追加写入。

以下是各列的定义，按顺序排列：

| 列序 | 列名 | 数据类型 | 说明 |
|------|------|---------|------|
| 1 | `code` | string | 股票代码，含交易所前缀（如 `sh600000`, `sz000001`） |
| 2 | `name` | string | 股票名称 |
| 3 | `open` | float | 今开盘价 |
| 4 | `close` | float | 昨收盘价 |
| 5 | `now` | float | 当前价 |
| 6 | `high` | float | 今最高价 |
| 7 | `low` | float | 今最低价 |
| 8 | `buy` | float | 竞买价（买一价） |
| 9 | `sell` | float | 竞卖价（卖一价） |
| 10 | `turnover` | int | 成交量（股） |
| 11 | `volume` | float | 成交额（元） |
| 12 | `bid1_volume` | int | 买一量 |
| 13 | `bid1` | float | 买一价 |
| 14 | `bid2_volume` | int | 买二量 |
| 15 | `bid2` | float | 买二价 |
| 16 | `bid3_volume` | int | 买三量 |
| 17 | `bid3` | float | 买三价 |
| 18 | `bid4_volume` | int | 买四量 |
| 19 | `bid4` | float | 买四价 |
| 20 | `bid5_volume` | int | 买五量 |
| 21 | `bid5` | float | 买五价 |
| 22 | `ask1_volume` | int | 卖一量 |
| 23 | `ask1` | float | 卖一价 |
| 24 | `ask2_volume` | int | 卖二量 |
| 25 | `ask2` | float | 卖二价 |
| 26 | `ask3_volume` | int | 卖三量 |
| 27 | `ask3` | float | 卖三价 |
| 28 | `ask4_volume` | int | 卖四量 |
| 29 | `ask4` | float | 卖四价 |
| 30 | `ask5_volume` | int | 卖五量 |
| 31 | `ask5` | float | 卖五价 |
| 32 | `date` | string | 日期（格式 `YYYY-MM-DD`） |
| 33 | `time` | string | 时间（格式 `HH:MM:SS`） |

## 使用 pandas 读取数据

```python
import pandas as pd
from config import CSV_COLUMNS

df = pd.read_csv(
    "data/2026-03-05/2026-03-05_trading.csv.gz",
    names=CSV_COLUMNS,
    header=None,
    compression="gzip",
)
```

## 文件命名规则

每日数据存储在以日期命名的子目录中，包含三个文件：

| 文件名 | 阶段 | 时间段 |
|--------|------|--------|
| `{date}_auction_open.csv.gz` | 早盘竞价 | 09:15 - 09:25 |
| `{date}_trading.csv.gz` | 连续交易 | 09:30 - 11:30, 13:00 - 14:57 |
| `{date}_auction_close.csv.gz` | 尾盘竞价 | 14:57 - 15:00 |

## 数据量估算

- 每帧约 5000 只股票 × 33 列
- 早盘竞价：约 67 帧（10 分钟 / 9 秒）
- 交易时间：约 1480 帧（4 小时 27 分钟 / 3 秒，含午休排除）
- 尾盘竞价：约 20 帧（3 分钟 / 9 秒）
- 每日合计约 1567 帧，约 780 万行原始数据
