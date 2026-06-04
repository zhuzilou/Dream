import os
from datetime import datetime
import pandas as pd
from loguru import logger

def generate_markdown_report(news_data: list[dict], report_dir: str = None):
    """
    将抓取到的新闻数据生成为 Markdown 文件
    news_data format: [{'id': 'xxx', 'title': 'xxx', 'content': 'xxx', 'time': 'xxx', 'source': 'xxx', 'analysis': {...}, 'plan': {...}}]
    """
    if not news_data:
        logger.info("No new news to generate report.")
        return

    if report_dir is None:
        # 兼容 Docker 容器和本地路径
        if os.path.exists("/app/data/reports"):
            report_dir = "/app/data/reports"
        else:
            report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "reports")

    os.makedirs(report_dir, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    report_file = os.path.join(report_dir, f"report_{today_str}.md")
    
    # 按照抓取批次追加写入，避免覆盖今天之前的数据
    is_new_file = not os.path.exists(report_file)
    
    try:
        with open(report_file, "a", encoding="utf-8") as f:
            if is_new_file:
                f.write(f"# Frank Gemini 股票智能监控 - {today_str} 简报\n\n")
            
            run_time = datetime.now().strftime("%H:%M:%S")
            f.write(f"## 抓取时间: {run_time}\n\n")
            
            for item in news_data:
                source_label = f"[{item.get('source', '未知来源')}] "
                title = item.get('title', '')
                if not title:
                    content = item.get('content', '')
                    title = content[:30] + "..." if len(content) > 30 else content
                    
                f.write(f"### {source_label}{title}\n")
                f.write(f"**时间:** {item.get('time', '未知时间')}\n\n")
                
                # 添加 AI 分析内容
                analysis = item.get('analysis')
                if analysis:
                    score = analysis.get('sentiment_score', 0)
                    emoji = "🚀利好" if score > 3 else ("⚠️利空" if score < -3 else "⚖️中性")
                    f.write(f"> **AI 分析结论 ({emoji} {score})**\n")
                    f.write(f"> - **核心总结**: {analysis.get('summary', '无')}\n")
                    f.write(f"> - **风险提示**: {analysis.get('devils_advocate', '无')}\n\n")

                # 添加策略建议 (如果有)
                plan = item.get('plan')
                if plan:
                    f.write(f"#### 🎯 策略建议\n")
                    f.write(f"- **操作建议**: {plan.get('action', '观察')}\n")
                    f.write(f"- **参考价格**: 买入 {plan.get('buy_price', '--')} | 止损 {plan.get('stop_loss', '--')} | 止盈 {plan.get('take_profit', '--')}\n")
                    f.write(f"- **推荐理由**: {plan.get('reason', '无')}\n\n")

                f.write(f"{item.get('content', '')}\n\n")
                f.write("---\n\n")
                
        logger.info(f"Successfully generated/updated report: {report_file} with {len(news_data)} items.")
    except Exception as e:
        logger.error(f"Error generating markdown report: {e}")
