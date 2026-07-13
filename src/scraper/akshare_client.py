import akshare as ak
import pandas as pd
from loguru import logger
import re
import time

def get_cls_telegraph() -> pd.DataFrame:
    """获取全球财经快讯数据 (原财联社电报，现切换为东财源以提高稳定性)"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching global financial news (Attempt {attempt+1})...")
            # 切换为东财源，财联社源目前 404
            df = ak.stock_info_global_em()
            if df is not None and not df.empty:
                return df
            time.sleep(2) 
        except Exception as e:
            logger.error(f"Error fetching global news (Attempt {attempt+1}): {e}")
            if attempt == max_retries - 1:
                return pd.DataFrame()
            time.sleep(5)
    return pd.DataFrame()

import time

def get_stock_news(symbol: str) -> pd.DataFrame:
    """获取指定股票代码（如 '300059'）的新闻"""
    try:
        logger.info(f"Fetching news for stock: {symbol}...")
        df = ak.stock_news_em(symbol=symbol)
        if df is not None and not df.empty:
            df['symbol'] = symbol
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}")
        return pd.DataFrame()

def _format_symbol(symbol: str) -> str:
    """将 6 位代码转换为新浪格式，如 sh600021, sz000001"""
    if symbol.startswith('6'):
        return f"sh{symbol}"
    else:
        return f"sz{symbol}"

def get_stock_hist(symbol: str, days: int = 60) -> pd.DataFrame:
    """获取历史日线数据 (新浪源)"""
    try:
        formatted_symbol = _format_symbol(symbol)
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        
        logger.info(f"Fetching hist data for {formatted_symbol}...")
        df = ak.stock_zh_a_daily(symbol=formatted_symbol, start_date=start_date, end_date=end_date, adjust="qfq")
        return df
    except Exception as e:
        logger.error(f"Error fetching hist data for {symbol}: {e}")
        return pd.DataFrame()

def get_stock_current_price(symbol: str) -> dict:
    """获取最新价格，支持降级机制"""
    result = {"price": 0.0, "source": "unknown", "is_fallback": False}
    
    # 尝试 1: 实时数据 (新浪源)
    try:
        formatted_symbol = _format_symbol(symbol)
        df = ak.stock_zh_a_spot()
        row = df[df['代码'] == formatted_symbol]
        if not row.empty:
            result["price"] = float(row.iloc[0]['最新价'])
            result["source"] = "realtime_sina"
            return result
    except Exception as e:
        logger.warning(f"Error fetching realtime price for {symbol}: {e}")

    # 尝试 2: 降级到历史日线 (取最后一根 K 线)
    try:
        logger.info(f"Triggering fallback to daily hist for {symbol}...")
        df_hist = get_stock_hist(symbol, days=5)
        if not df_hist.empty:
            result["price"] = float(df_hist.iloc[-1]['close'])
            result["source"] = "daily_hist_fallback"
            result["is_fallback"] = True
            return result
    except Exception as e:
        logger.error(f"Fallback failed for {symbol}: {e}")

    return result

def get_stock_audit_data(symbol: str) -> dict:
    """获取审计所需的实时数据：当前价、涨跌幅、换手率、5日涨跌幅"""
    data = {
        "price": 0.0,
        "change_pct": 0.0,
        "turnover": 0.0,
        "five_day_change": 0.0,
        "is_fallback": False
    }
    try:
        # 1. 实时数据 (东财源通常包含换手率)
        try:
            df_spot = ak.stock_zh_a_spot_em()
            row = df_spot[df_spot['代码'] == symbol]
            if not row.empty:
                data["price"] = float(row.iloc[0]['最新价'])
                data["change_pct"] = float(row.iloc[0]['涨跌幅'])
                data["turnover"] = float(row.iloc[0]['换手率'])
        except Exception as e:
            logger.warning(f"Error fetching spot data from EM for {symbol}: {e}")
            # 退而求其次使用主价格获取函数 (自带降级)
            price_res = get_stock_current_price(symbol)
            data["price"] = price_res["price"]
            data["is_fallback"] = price_res["is_fallback"]

        # 2. 5日涨跌幅
        df_hist = get_stock_hist(symbol, days=15) 
        if not df_hist.empty and len(df_hist) >= 6:
            latest_close = float(df_hist.iloc[-1]['close'])
            five_days_ago_close = float(df_hist.iloc[-6]['close'])
            data["five_day_change"] = round((latest_close - five_days_ago_close) / five_days_ago_close * 100, 2)
            
            # 如果上方实时数据获取失败，这里也可以补充 price
            if data["price"] == 0:
                data["price"] = latest_close
                data["is_fallback"] = True
            
    except Exception as e:
        logger.error(f"Error fetching audit data for {symbol}: {e}")
    
    return data

# 内存缓存，避免频繁调用 slow API
_STOCK_LIST_CACHE = None

def _get_full_stock_list():
    global _STOCK_LIST_CACHE
    if _STOCK_LIST_CACHE is not None:
        return _STOCK_LIST_CACHE
    
    try:
        df = ak.stock_info_a_code_name()
        if df is not None and not df.empty:
            _STOCK_LIST_CACHE = df
            return df
    except Exception as e:
        logger.error(f"Error fetching full stock list: {e}")
    return pd.DataFrame()

def resolve_stock_symbol(query: str) -> dict:
    """
    根据名称或代码模糊匹配股票。
    返回: {'symbol': 'xxx', 'name': 'xxx'} 或 None
    """
    try:
        query = query.strip()
        # 1. 如果本身就是 6 位数字代码
        if re.match(r'^\d{6}$', query):
            df = _get_full_stock_list()
            if not df.empty:
                row = df[df['code'] == query]
                if not row.empty:
                    return {'symbol': query, 'name': row.iloc[0]['name']}
            return {'symbol': query, 'name': '未知'}

        # 2. 如果是中文名称，尝试匹配
        logger.info(f"Resolving stock symbol for name: {query}")
        df = _get_full_stock_list()
        if df.empty:
            return None
            
        # 模糊匹配名称
        matches = df[df['name'].str.contains(query, na=False)]
        
        if matches.empty:
            return None
        
        # 如果有多条匹配，优先选完全一致的
        exact_match = matches[matches['name'] == query]
        if not exact_match.empty:
            return {'symbol': exact_match.iloc[0]['code'], 'name': exact_match.iloc[0]['name']}
        
        # 否则返回第一条模糊匹配
        return {'symbol': matches.iloc[0]['code'], 'name': matches.iloc[0]['name']}
    except Exception as e:
        logger.error(f"Error resolving stock symbol for {query}: {e}")
        return None

def get_market_index_data() -> pd.DataFrame:
    """获取主要大盘指数实时数据"""
    try:
        # 获取指数行情 (东财源)
        df = ak.stock_zh_index_spot_em()
        # 常见指数代码：上证(000001), 创业板(399006), 深证成指(399001)
        target_indices = ['000001', '399006', '399001']
        if df is not None and not df.empty:
            return df[df['代码'].isin(target_indices)]
    except Exception as e:
        logger.error(f"Error fetching market index data: {e}")
    return pd.DataFrame()


def collect_board_observation_inputs(max_boards: int = 3) -> list:
    """采集场景二所需的板块与成份股结构化输入。"""
    boards = []
    try:
        board_df = ak.stock_board_industry_name_em()
        if board_df is None or board_df.empty:
            return boards

        for _, row in board_df.head(max_boards).iterrows():
            board_name = _first_present(row, ["板块名称", "名称", "行业名称"])
            if not board_name:
                continue

            stocks = []
            try:
                cons_df = ak.stock_board_industry_cons_em(symbol=board_name)
                if cons_df is not None and not cons_df.empty:
                    for _, stock_row in cons_df.head(10).iterrows():
                        name = str(_first_present(stock_row, ["名称", "股票简称", "证券简称"]) or "")
                        stocks.append({
                            "symbol": str(_first_present(stock_row, ["代码", "股票代码", "证券代码"]) or ""),
                            "name": name,
                            "turnover": _safe_float(_first_present(stock_row, ["成交额", "成交金额"])),
                            "change_pct": _safe_float(_first_present(stock_row, ["涨跌幅", "涨幅"])),
                            "is_st": "ST" in name.upper(),
                            "is_suspended": False
                        })
            except Exception as e:
                logger.warning(f"Error fetching board constituents for {board_name}: {e}")

            boards.append({
                "board_name": str(board_name),
                "change_pct": _safe_float(_first_present(row, ["涨跌幅", "涨幅"])),
                "net_inflow": _safe_float(_first_present(row, ["主力净流入", "净流入", "资金净流入"])),
                "turnover": _safe_float(_first_present(row, ["成交额", "成交金额"])),
                "sustainability": 0.5,
                "beginner_friendliness": 0.5,
                "stocks": stocks
            })
    except Exception as e:
        logger.error(f"Error collecting board observation inputs: {e}")
    return boards


def _first_present(row, keys):
    for key in keys:
        try:
            if key in row and row[key] is not None:
                return row[key]
        except Exception:
            continue
    return None


def _safe_float(value):
    try:
        if value in [None, ""]:
            return 0.0
        return float(value)
    except Exception:
        return 0.0
