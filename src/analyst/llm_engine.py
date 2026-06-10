import os
import requests
import json
from loguru import logger

class Analyst:
    def __init__(self):
        self.api_key = os.getenv("MINIMAX_API_KEY")
        self.base_url = "https://api.minimax.chat/v1/text/chatcompletion_v2"

    def chat(self, user_input):
        """通用问答接口，用于处理非特定指令的询问"""
        if not self.api_key:
            return "API Key 未配置，无法回答。"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": "MiniMax-M2.7", 
            "messages": [
                {"role": "system", "content": "你是一个名为 Frank Gemini 的 A 股投资助手。你专业、幽默，擅长通过技术面和基本面分析市场。在分析审核时，请使用清晰的结构，并用【】或 ** 来标注核心观点，适当使用表情符号引导阅读。回复请尽量简洁，重点突出。"},
                {"role": "user", "content": user_input}
            ]
        }

        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            if "choices" in result and result["choices"]:
                return result['choices'][0]['message']['content'].strip()
            return "抱歉，我现在有点走神，没能理解您的话。"
        except Exception as e:
            logger.error(f"Chat API error: {e}")
            return "抱歉，我的大脑连接出了点小问题。"

    def analyze_news(self, title, content, symbol=""):
        """
        使用 MiniMax 对新闻进行情绪分析
        资深分析师模式：过滤杂音，直击核心逻辑，提供“推演建筑师”所需的基础分析。
        """
        if not self.api_key:
            logger.error("MINIMAX_API_KEY not found.")
            return None

        prompt = f"""
你是一名在 A 股市场深耕 20 年的资深首席分析师。你的任务是分析以下新闻对股票 {symbol if symbol else '相关行业'} 的真实、深层次影响，并过滤掉那些“大家都知道”的平庸信息。

新闻标题：{title}
新闻内容：{content}

你的职责：
1. **去伪存真**：如果新闻只是陈词滥调，请在 summary 中直言其影响力有限。
2. **逻辑穿透**：分析该事件会如何通过产业链或资金面传导至二级市场股价。
3. **极端假设**：强制执行“魔鬼代言人”模式，假设你是空头，你会如何利用这条新闻攻击该标的？

请按以下格式输出 JSON：
{{
  "sentiment_score": 小数 (范围 -10 到 10，-10 为极端利空，10 为极端利好),
  "analysis": "核心逻辑链分析 (100字以内)",
  "devils_advocate": "极端风险推演/空头视角",
  "summary": "资深分析师的一句话定调 (如：'典型的利好出尽'，'被市场忽视的关键拐点' 等)"
}}
注意：输出必须仅为 JSON 格式。确保 JSON 字段值的双引号被正确转义。
"""
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": "MiniMax-M2.7", 
            "messages": [
                {"role": "system", "content": "你是一个专业的股票分析助手，擅长客观分析新闻影响。你必须输出合法的 JSON 格式，确保内部字符串中的双引号被正确转义。"},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and result["choices"]:
                content_str = result['choices'][0]['message']['content']
                # 清洗 Markdown 代码块标签
                content_str = content_str.replace("```json", "").replace("```", "").strip()
                
                try:
                    analysis_data = json.loads(content_str)
                    return analysis_data
                except json.JSONDecodeError:
                    # 尝试进行简单的修复：处理属性值中未转义的双引号
                    logger.warning("Standard JSON parse failed, attempting repair...")
                    # 匹配 "key": "value" 结构，尝试修复 value 中的未转义引号
                    import re
                    # 这是一个简单的启发式修复，寻找被引号包围的属性值
                    def fix_quotes(match):
                        key = match.group(1)
                        value = match.group(2)
                        # 将 value 中非转义的引号转义
                        fixed_value = re.sub(r'(?<!\\)"', r'\"', value)
                        return f'"{key}": "{fixed_value}"'
                    
                    repaired_str = re.sub(r'"(\w+)":\s*"(.+?)"(?=\s*[,}])', fix_quotes, content_str, flags=re.S)
                    try:
                        return json.loads(repaired_str)
                    except:
                        logger.error(f"Failed to repair JSON: {content_str}")
                        return None
            else:
                logger.error(f"Invalid MiniMax response: {result}")
                return None
        except Exception as e:
            logger.error(f"Error calling MiniMax API: {e}")
            if 'response' in locals():
                logger.error(f"API Response: {response.text}")
            return None
