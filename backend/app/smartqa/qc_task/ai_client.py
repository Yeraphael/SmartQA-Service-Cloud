"""阿里通义千问AI客户端。"""

import json
import os
from typing import Any

from app.config.setting import settings

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class QwenClient:
    """阿里通义千问模型客户端（通过OpenAI兼容接口）。"""

    def __init__(self):
        """初始化客户端。"""
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ALI_MODEL_API_KEY") or settings.OPENAI_API_KEY
        self.base_url = (
            os.getenv("OPENAI_BASE_URL")
            or os.getenv("ALI_MODEL_ENDPOINT")
            or settings.OPENAI_BASE_URL
            or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        if OpenAI is None:
            raise ImportError("openai package not installed. Please install it: pip install openai")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    async def call_model(
        self,
        model_name: str,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> dict[str, Any]:
        """调用阿里通义千问模型。

        Args:
            model_name: 模型名称，如 qwen-plus、qwen-turbo
            prompt: 输入提示词
            temperature: 温度参数，控制随机性
            max_tokens: 最大输出token数

        Returns:
            包含响应内容和元数据的字典
        """
        try:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的客服质检助手，负责分析客服聊天记录并给出客观、准确的质检评价。你必须严格按照JSON格式输出结果，不要输出任何Markdown或解释性文本。",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

            raw_text = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            return {
                "success": True,
                "raw_text": raw_text,
                "response": json.loads(raw_text) if raw_text else {},
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "model": response.model,
            }

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON解析失败: {str(e)}",
                "raw_text": raw_text if 'raw_text' in locals() else "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"模型调用失败: {str(e)}",
            }

    def is_available(self) -> bool:
        """检查AI客户端是否可用。"""
        return bool(self.api_key and OpenAI)
