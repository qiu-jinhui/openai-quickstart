from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain

from utils import LOG
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
import os

class TranslationChain:
    def __init__(self, model_name: str = "gpt-3.5-turbo", verbose: bool = True):
        
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

        # 为了翻译结果的稳定性，将 temperature 设置为 0
        chat = ChatOpenAI(
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name=model_name, temperature=0, verbose=verbose)

        self.chain = LLMChain(llm=chat, prompt=chat_prompt_template, verbose=verbose)
        
        # 添加不同翻译风格的指令
        self.style_instructions = {
            "standard": "Please translate the text in a standard, accurate way.",
            "novel": "Please translate the text in the style of a novel, with literary, expressive language and narrative flow.",
            "news": "Please translate the text in a news article style, with clear, concise, and objective language.",
            "academic": "Please translate the text in an academic style, with formal language, precise terminology, and logical structure.",
            "casual": "Please translate the text in a casual, conversational style, as if speaking to a friend.",
            "poetic": "Please translate the text in a poetic style, with attention to rhythm, imagery, and emotional resonance.",
            "technical": "Please translate the text in a technical style, with precise terminology and clear explanations.",
            "humorous": "Please translate the text with a humorous tone, incorporating wit and playfulness where appropriate."
        }

    def run(self, text: str, source_language: str, target_language: str, translation_style: str = "standard") -> (str, bool):
        result = ""
        try:
            # 获取指定风格的指令，如果没有找到就使用标准风格
            style_instruction = self.style_instructions.get(translation_style, self.style_instructions["standard"])
            
            result = self.chain.run({
                "text": text,
                "source_language": source_language,
                "target_language": target_language,
                "style_instruction": style_instruction
            })
        except Exception as e:
            LOG.error(f"An error occurred during translation: {e}")
            return result, False

        return result, True