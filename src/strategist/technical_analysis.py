import pandas as pd
import numpy as np
from loguru import logger

def calculate_ma(df: pd.DataFrame, periods=[5, 10, 20]):
    """计算简单移动平均线"""
    for p in periods:
        df[f'MA{p}'] = df['close'].rolling(window=p).mean()
    return df

def get_support_resistance(df: pd.DataFrame):
    """简单计算支撑和压力位 (基于近期高低点)"""
    recent_df = df.tail(20) # 最近 20 个交易日
    support = recent_df['low'].min()
    resistance = recent_df['high'].max()
    return support, resistance

def analyze_trend(df: pd.DataFrame):
    """分析当前趋势"""
    if len(df) < 20:
        return "数据不足"
    
    last_row = df.iloc[-1]
    ma5 = last_row['MA5']
    ma20 = last_row['MA20']
    close = last_row['close']
    
    if close > ma5 > ma20:
        return "多头排列 (强趋势)"
    elif close < ma5 < ma20:
        return "空头排列 (弱趋势)"
    elif close > ma20:
        return "震荡偏强"
    else:
        return "震荡偏弱"
