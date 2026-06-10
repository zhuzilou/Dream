import os
from dotenv import load_dotenv
load_dotenv() # 加载 .env 文件中的环境变量

import sqlite3
import time
import schedule
import threading
from loguru import logger
import hashlib
from scraper.akshare_client import get_stock_news, get_stock_hist, get_stock_current_price, get_market_index_data
from generator.markdown_gen import generate_markdown_report
from notifier.feishu import FeishuBot
from analyst.llm_engine import Analyst
from strategist.trade_advisor import TradeAdvisor
from listener.feishu_listener import FeishuListener

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "scout.db")
if os.path.exists("/app/data/scout.db"):
    DB_PATH = "/app/data/scout.db"

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "app.log")
if os.path.exists("/app/logs"):
    LOG_PATH = "/app/logs/app.log"
elif os.path.exists("/app/data/logs"):
    LOG_PATH = "/app/data/logs/app.log"

# Configure loguru
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logger.add(
    LOG_PATH, 
    rotation="00:00", 
    retention="10 days", 
    level="INFO", 
    encoding="utf-8", 
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
)

def get_all_target_symbols():
    """从数据库获取所有需要监控的股票代码与名称 (观察池 + 持仓池)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    symbols = {} # {symbol: name}
    # 观察池
    cursor.execute('SELECT symbol, name FROM watchlist WHERE status = "active"')
    for row in cursor.fetchall():
        symbols[row[0]] = row[1] or row[0]
    # 持仓池
    cursor.execute('SELECT symbol, name FROM positions')
    for row in cursor.fetchall():
        symbols[row[0]] = row[1] or row[0]
    conn.close()
    
    # 如果数据库为空，返回默认值
    if not symbols:
        return {"301667": "纳百川", "600021": "上海电力"}
    return symbols

def init_db():
    if DB_PATH != ":memory:":
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 历史新闻表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id TEXT PRIMARY KEY,
            source TEXT,
            timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
            analysis TEXT
        )
    ''')
    # 观察池表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            added_at DATETIME DEFAULT (datetime('now', 'localtime')),
            strategy_type TEXT DEFAULT 'default',
            status TEXT DEFAULT 'active'
        )
    ''')
    # 持仓表 (增加了 quantity, last_known_price, last_updated)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            entry_price REAL,
            quantity REAL DEFAULT 0,
            entry_date DATETIME DEFAULT (datetime('now', 'localtime')),
            stop_loss REAL,
            take_profit REAL,
            last_known_price REAL,
            last_updated DATETIME,
            current_strategy TEXT DEFAULT 'default',
            risk_level INTEGER DEFAULT 3
        )
    ''')

    # 交易记录表 (新)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            name TEXT,
            action TEXT,
            price REAL,
            quantity REAL,
            reason TEXT,
            timestamp DATETIME DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    
    # 数据库迁移逻辑：检查并添加 missing columns
    # 检查 watchlist 表
    cursor.execute("PRAGMA table_info(watchlist)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'name' not in columns:
        logger.info("Migrating database: adding 'name' column to 'watchlist' table")
        cursor.execute("ALTER TABLE watchlist ADD COLUMN name TEXT")
    
    # 检查 positions 表
    cursor.execute("PRAGMA table_info(positions)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'name' not in columns:
        logger.info("Migrating database: adding 'name' column to 'positions' table")
        cursor.execute("ALTER TABLE positions ADD COLUMN name TEXT")
    if 'quantity' not in columns:
        logger.info("Migrating database: adding 'quantity' column to 'positions' table")
        cursor.execute("ALTER TABLE positions ADD COLUMN quantity REAL DEFAULT 0")
    if 'last_known_price' not in columns:
        logger.info("Migrating database: adding 'last_known_price' column to 'positions' table")
        cursor.execute("ALTER TABLE positions ADD COLUMN last_known_price REAL")
    if 'last_updated' not in columns:
        logger.info("Migrating database: adding 'last_updated' column to 'positions' table")
        cursor.execute("ALTER TABLE positions ADD COLUMN last_updated DATETIME")

    # 插入默认监控 (如果为空)
    cursor.execute('SELECT COUNT(*) FROM watchlist')
    if cursor.fetchone()[0] == 0:
        cursor.execute('SELECT COUNT(*) FROM positions')
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO watchlist (symbol, name) VALUES (?, ?)', ("301667", "纳百川"))
            cursor.execute('INSERT INTO watchlist (symbol, name) VALUES (?, ?)', ("600021", "上海电力"))
            
    conn.commit()
    conn.close()

def get_position_by_symbol(symbol):
    """从数据库获取指定股票的持仓信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT quantity, entry_price FROM positions WHERE symbol = ?', (symbol,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"quantity": row[0], "entry_price": row[1]}
    return None

def is_news_processed(news_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM news WHERE id = ?', (news_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_news_processed(news_id: str, source: str, analysis: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO news (id, source, timestamp, analysis) VALUES (?, ?, datetime("now", "localtime"), ?)', (news_id, source, analysis))
    conn.commit()
    conn.close()

def generate_id(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def job():
    logger.info("Starting scheduled news fetching job for Frank Gemini...")
    init_db()
    
    feishu = FeishuBot()
    chat_id = os.getenv("FEISHU_CHAT_ID")
    analyst = Analyst()
    advisor = TradeAdvisor()
    
    # 0. 大盘波动监测 (主动哨兵模式)
    index_df = get_market_index_data()
    if not index_df.empty and chat_id:
        for _, row in index_df.iterrows():
            change_pct = float(row.get('涨跌幅', 0))
            name = row.get('名称', '指数')
            if change_pct <= -1.0: # 跌幅超过 1% 触发定心丸
                logger.warning(f"Market crash detected: {name} {change_pct}%")
                # AI 分析大盘
                analysis = analyst.chat(f"当前{name}跌幅达 {change_pct}%，作为首席分析师，请简要分析下跌原因并给出心理支撑。")
                title = f"🚨 大盘波动警报 | {name} 紧急定心丸"
                md_text = f"**【波动情况】**: {name} 当前跌幅 **{change_pct}%**\n\n"
                md_text += f"**【分析师说】**:\n{analysis}\n\n"
                md_text += f"**【推演预案】**: 此时建议保持冷静，检查个股是否触及硬损位，未触及则建议卧倒不动。详情请看下方个股推演。"
                feishu.send_interactive_message(chat_id, title, md_text, receive_id_type="chat_id")

    new_items = []
    
    # 1. 移除全球财经快讯 (用户认为其信息密度低且大家都知道)
    # 此处不再调用 get_cls_telegraph()

    # 2. 抓取个股新闻并生成策略推演
    symbols_map = get_all_target_symbols()
    for symbol, name in symbols_map.items():
        news_df = get_stock_news(symbol)
        if not news_df.empty:
            for _, row in news_df.head(5).iterrows():
                title = str(row.get('新闻标题', row.get('title', '')))
                content = str(row.get('新闻内容', row.get('content', '')))
                pub_time = str(row.get('发布时间', row.get('time', '')))
                
                if not title: continue
                news_id = generate_id(f"em_{symbol}_{pub_time}_{title}")
                
                if not is_news_processed(news_id):
                    # 获取行情数据进行建模
                    hist_df = get_stock_hist(symbol)
                    price_res = get_stock_current_price(symbol)
                    current_pos = get_position_by_symbol(symbol)
                    
                    # AI 分析 (采用资深分析师角色)
                    analysis = analyst.analyze_news(title, content, symbol=f"{name}({symbol})")
                    
                    # 生成推演预案 (Scenario Architect)
                    plan = advisor.generate_plan(symbol, price_res, hist_df, analysis, current_pos=current_pos) if analysis else None
                    
                    new_items.append({
                        'id': news_id, 'title': title, 'content': content, 
                        'time': pub_time, 'source': f'{name}', 
                        'analysis': analysis, 'plan': plan
                    })
                    import json
                    mark_news_processed(news_id, f'东方财富-{name}', json.dumps(analysis) if analysis else "")

    # 3. 推送定心丸推演卡片
    if new_items:
        feishu = FeishuBot()
        chat_id = os.getenv("FEISHU_CHAT_ID")
        if chat_id:
            for item in new_items[:3]:
                plan = item.get('plan')
                analysis = item.get('analysis')
                if plan:
                    # 构造“推演建筑师”卡片内容
                    title = f"🕵️‍♂️ Frank | {item['source']} 深度推演预案"
                    
                    # 核心逻辑总结 (倾向B)
                    summary = analysis.get('summary', '无摘要')
                    
                    # 构造推演 Markdown (倾向C)
                    md_text = f"**【核心结论】**\n{summary}\n\n"
                    md_text += f"**【当前价】**: {plan['current_price']} 元\n"
                    md_text += f"**【当前建议】**: **{plan['action']}**\n\n"
                    
                    # 从 plan 中提取推演逻辑 (稍后会在 advisor 中增强)
                    md_text += f"**【操作推演 (Scenario Architect)】**\n"
                    md_text += f"{plan.get('scenario_text', plan['reason'])}\n\n"
                    
                    md_text += f"**【风险防御】**\n{analysis.get('devils_advocate', '暂无')}"
                    
                    feishu.send_interactive_message(chat_id, title, md_text, receive_id_type="chat_id")
    else:
        logger.info("Job completed. No new news.")

def run_scheduler():
    schedule.every().day.at("08:30").do(job)
    schedule.every().day.at("12:30").do(job)
    schedule.every().day.at("18:30").do(job)
    while True:
        schedule.run_pending()
        time.sleep(60)

def main():
    logger.info("Frank Gemini is running with Strategist upgrade...")
    
    # 0. 初始化数据库 (确保表结构存在)
    init_db()
    
    # 1. 启动定时抓取 (后台线程)
    def background_tasks():
        run_scheduler() # 仅进入定时循环，不再启动即跑一次
        
    bg_thread = threading.Thread(target=background_tasks, daemon=True)
    bg_thread.start()
    
    # 2. 启动飞书 WebSocket 监听 (主线程阻塞)
    listener = FeishuListener()
    listener.start()

if __name__ == "__main__":
    main()
