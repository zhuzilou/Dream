import os
import requests
import json
from loguru import logger

class RiskAuditor:
    def __init__(self):
        self.api_key = os.getenv("MINIMAX_API_KEY")
        self.base_url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
        self.system_prompt = (
            "你是 Frank Gemini 的 A 股风险校准员。你的任务是帮助用户复核投资逻辑、研报内容或资讯，"
            "识别风险、校准数据时点，并提供辅助决策信息。\n"
            "你的风格：冷静、专业、克制、对事实严格，但表达要人性化。\n"
            "你的核心准则：\n"
            "1. 区分事实错误、逻辑风险和时效偏差。市场快速变化导致的行情差异，默认视为时效偏差，"
            "不得归咎于数据提供者，除非内容存在股票代码错误、字段缺失或明显不可能的事实。\n"
            "2. 用户或其他机器人提供的数据可作为历史上下文；当前市场数据只代表 Frank 分析时点，"
            "用于校准风险和辅助决策，不用于追责原始信息来源。\n"
            "3. 对乐观预期保持审慎，指出反向风险，但避免使用“误导”“不准确”“错误”等归责性结论，"
            "除非已有明确证据。\n"
            "4. 如果提供了实时行情数据（价格、涨跌幅、换手率等），请说明它与原始内容可能存在时间差，"
            "并标注哪些结论仍可参考、哪些需要重新确认。\n"
            "5. 回复结构建议包含：**时效性说明**、**当前行情校准**、**仍可参考的逻辑**、"
            "**主要风险**、**辅助决策建议**。重点突出，使用 **加粗** 强调关键词。"
        )

    def audit(self, content, market_context=""):
        """执行极端反向审计"""
        if not self.api_key:
            return "API Key 未配置，无法执行审计。"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        user_input = f"**待审核内容**：\n{content}\n\n"
        if market_context:
            user_input += f"**当前市场实时数据参考**：\n{market_context}\n\n"
        user_input += "请开始你的风险校准报告。"

        payload = {
            "model": "MiniMax-M2.7", 
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_input}
            ]
        }

        try:
            logger.info("Triggering RiskAuditor audit...")
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            if "choices" in result and result["choices"]:
                return result['choices'][0]['message']['content'].strip()
            return "审计官陷入了沉思，未能给出报告。"
        except Exception as e:
            logger.error(f"RiskAuditor API error: {e}")
            return "审计官的大脑连接出了点小问题，无法完成报告。"
