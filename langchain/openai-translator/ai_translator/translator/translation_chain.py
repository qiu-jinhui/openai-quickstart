from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain

from utils import LOG
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
import os
import re
import zhipuai
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    SystemMessage,
)
from typing import Any, Dict, List, Mapping, Optional, Union
from pydantic import Field

class ZhipuAIModel:
    """智谱AI模型的简单封装，直接使用ZhipuAI API而不通过LangChain。
    
    这种方法避免了LangChain的BaseChatModel可能带来的兼容性问题。
    """
    def __init__(self, model_name: str, api_key: str, temperature: float = 0.0, verbose: bool = False):
        self.model_name = model_name
        self.api_key = api_key
        self.temperature = temperature
        self.verbose = verbose
        # 初始化客户端
        self.client = zhipuai.ZhipuAI(api_key=self.api_key)
    
    def generate(self, messages: List[Dict[str, str]]) -> str:
        """调用智谱AI API生成回复
        
        Args:
            messages: 消息列表，格式为[{"role": "system", "content": "..."}, ...]
            
        Returns:
            str: 生成的回复内容
        """
        try:
            if self.verbose:
                LOG.debug(f"ZhipuAI messages: {messages}")
            
            # 调用聊天补全API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                top_p=0.7
            )
            
            if self.verbose:
                LOG.debug(f"ZhipuAI response: {response}")
            
            # 提取回复内容
            content = response.choices[0].message.content
            return content
            
        except Exception as e:
            LOG.error(f"ZhipuAI API调用失败: {str(e)}")
            raise e

class TranslationChain:
    def __init__(self, model_name: str = "gpt-3.5-turbo", verbose: bool = True):
        
        # 风格指令字典
        self.style_instructions = {
            "standard": "Please translate the text in a standard, accurate way.",
            "academic": "Please translate the text in a formal, academic tone, suitable for scholarly papers.",
            "casual": "Please translate the text in a casual, conversational tone.",
            "technical": "Please translate the text with precise technical terminology.",
            "poetic": "Please translate the text in a poetic, literary style that preserves artistic elements.",
            "humorous": "Please translate the text with a humorous tone where appropriate.",
            "news": "Please translate the text in a clear, journalistic style appropriate for news articles.",
            "novel": "Please translate the text in a narrative style appropriate for novels or stories."
        }
        
        self.verbose = verbose
        
        # 检查模型名称是否包含GLM，如果是则使用智谱AI的模型
        if "glm" in model_name.lower():
            try:
                # 使用智谱AI GLM模型
                LOG.info(f"Using GLM model: {model_name}")
                # 获取智谱AI API密钥，通常是环境变量中的"ZHIPUAI_API_KEY"
                api_key = os.getenv("ZHIPUAI_API_KEY")
                if not api_key:
                    raise ValueError("ZHIPUAI_API_KEY environment variable is not set")
                
                # 初始化智谱AI模型
                self.model = ZhipuAIModel(
                    model_name=model_name,
                    api_key=api_key,
                    temperature=0,  # 为了翻译结果的稳定性，将 temperature 设置为 0
                    verbose=verbose
                )
                self.model_type = "zhipuai"
            except Exception as e:
                LOG.error(f"Error initializing GLM model: {e}")
                LOG.warning("Falling back to OpenAI model gpt-3.5-turbo")
                # 如果GLM初始化失败，回退到使用OpenAI模型
                self.model_type = "openai"
                self.chat = ChatOpenAI(
                    base_url=os.getenv("OPENAI_BASE_URL"),
                    api_key=os.getenv("OPENAI_API_KEY"),
                    model_name="gpt-3.5-turbo", 
                    temperature=0, 
                    verbose=verbose
                )
        else:
            # 使用OpenAI模型
            LOG.info(f"Using OpenAI model: {model_name}")
            self.model_type = "openai"
            self.chat = ChatOpenAI(
                base_url=os.getenv("OPENAI_BASE_URL"),
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name=model_name, temperature=0, verbose=verbose)
            
            # 翻译任务指令始终由 System 角色承担
            template = (
                """You are a translation expert, proficient in various languages. \n
                Translates {source_language} to {target_language}.\n
                {style_instruction}"""
            )
            system_message_prompt = SystemMessagePromptTemplate.from_template(template)

            # 待翻译文本由 Human 角色输入
            human_template = "{text}"
            human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

            # 使用 System 和 Human 角色的提示模板构造 ChatPromptTemplate
            chat_prompt_template = ChatPromptTemplate.from_messages(
                [system_message_prompt, human_message_prompt]
            )
            
            self.chain = LLMChain(llm=self.chat, prompt=chat_prompt_template, verbose=verbose)

    def run(self, text: str, source_language: str, target_language: str, translation_style: str = "standard") -> (str, bool):
        """使用翻译链进行翻译，支持不同的模型类型"""
        try:
            # 获取指定风格的指令，如果没有找到就使用标准风格
            style_instruction = self.style_instructions.get(translation_style, self.style_instructions["standard"])
            
            # 根据模型类型选择不同的翻译方法
            if self.model_type == "zhipuai":
                # 使用智谱AI模型
                system_message = {
                    "role": "system",
                    "content": f"""You are a translation expert, proficient in various languages. 
                    Translates {source_language} to {target_language}.
                    {style_instruction}
                    IMPORTANT: Do not add any prefixes like "Translation:" or "Here is the translation:". Just provide the translated content directly.
                    """
                }
                user_message = {"role": "user", "content": text}
                result = self.model.generate([system_message, user_message])
            else:
                # 使用OpenAI模型
                input_dict = {
                    "text": text,
                    "source_language": source_language,
                    "target_language": target_language,
                    "style_instruction": f"{style_instruction} IMPORTANT: Do not add any prefixes like 'Translation:' or 'Here is the translation:'. Just provide the translated content directly."
                }
                result = self.chain.run(input_dict)
            
            # 处理结果，移除可能的前缀
            if isinstance(result, str):
                # 常见的翻译前缀列表
                prefixes = [
                    "Here is the translation of the provided text into Chinese:",
                    "Here is the translation of the provided text:",
                    "Here is the Chinese translation:",
                    "Here is the translation:",
                    "Translation:",
                    "翻译:",
                    "翻译结果：",
                    "译文："
                ]
                
                # 检查并移除前缀
                for prefix in prefixes:
                    if result.strip().startswith(prefix):
                        result = result[len(prefix):].strip()
            
            LOG.debug(f"Translation successful. Result type: {type(result)}")
            return result, True
            
        except Exception as e:
            LOG.error(f"An error occurred during translation: {e}")
            return "", False