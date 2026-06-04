# 数据库架构设计 V2.0 (Strategist 2.0)

**日期：2026年5月18日**
**状态：草案 (Draft)**

---

## 1. 概述
为了支持动态监控池管理和智能仓位风控，数据库需要从单一的 `news` 记录扩展为包含 `watchlist` (观察池) 和 `positions` (持仓池) 的关系型结构。

## 2. 表结构设计

### 2.1 `watchlist` (观察池)
用于存储用户感兴趣、需要 AI 跟踪的股票。
- `symbol` (TEXT, PRIMARY KEY): 股票代码 (如 301667)
- `name` (TEXT): 股票名称
- `added_at` (DATETIME): 加入时间
- `strategy_type` (TEXT): 策略倾向 (如 "趋势", "博弈", "默认")
- `status` (TEXT): 状态 (如 "active", "paused")

### 2.2 `positions` (持仓池)
用于存储已买入的股票，开启高频风控监控。
- `symbol` (TEXT, PRIMARY KEY): 股票代码
- `entry_price` (REAL): 成本价
- `entry_date` (DATETIME): 买入时间
- `stop_loss` (REAL): 止损位 (动态调整)
- `take_profit` (REAL): 止盈位 (动态调整)
- `current_strategy` (TEXT): AI 判定的当前策略性格 (如 "宽幅回撤容忍")
- `risk_level` (INTEGER): 风险等级 (1-5)

### 2.3 `news` (历史新闻 - 已存在)
保持现状，用于去重和回溯。

---

## 3. 指令映射关系

| 飞书指令 | 逻辑操作 |
| :--- | :--- |
| `监控 301667` | 插入 `watchlist` |
| `买入 301667 105.5` | 从 `watchlist` 移至 `positions` (或直接插入)，计算初始 SL/TP |
| `卖出 301667` | 从 `positions` 移除 |
| `池子` | 查询 `watchlist` 和 `positions` 列表 |

---

## 4. 迁移计划
1.  初始化新表。
2.  修改 `src/main.py` 中的 `TARGET_SYMBOLS` 逻辑，改为从 `watchlist` 和 `positions` 动态读取。
3.  更新 `src/listener/feishu_listener.py` 增加指令解析。
