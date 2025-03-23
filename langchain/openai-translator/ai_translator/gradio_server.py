import sys
import os
import gradio as gr

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import ArgumentParser, LOG
from translator import PDFTranslator, TranslationConfig


def translation(input_file, model_name, zhipuai_api_key, source_language, target_language, translation_style):
    LOG.debug(f"[翻译任务]\n源文件: {input_file.name}\n模型: {model_name}\n源语言: {source_language}\n目标语言: {target_language}\n翻译风格: {translation_style}")
    
    # 如果选择了ChatGLM模型，并且提供了API密钥，则设置环境变量
    if "chatglm" in model_name.lower() and zhipuai_api_key:
        os.environ['ZHIPUAI_API_KEY'] = zhipuai_api_key
        LOG.info("ZHIPUAI_API_KEY environment variable has been set")
    
    # 使用选择的模型创建一个新的翻译器实例
    translator = PDFTranslator(model_name)
    
    output_file_path = translator.translate_pdf(
        input_file.name, source_language=source_language, target_language=target_language, translation_style=translation_style)

    return output_file_path

def launch_gradio():
    # 定义可用的翻译风格
    translation_styles = [
        "standard",  # 标准
        "novel",     # 小说
        "news",      # 新闻稿
        "academic",  # 学术
        "casual",    # 口语化
        "poetic",    # 诗歌
        "technical", # 技术文档
        "humorous"   # 幽默
    ]
    
    # 定义可用的模型
    available_models = [
        "glm-4",        # 智谱AI GLM-4模型
        "glm-3-turbo",  # 智谱AI GLM-3模型
        "gpt-3.5-turbo",   # OpenAI GPT-3.5
        "gpt-4",           # OpenAI GPT-4
    ]

    iface = gr.Interface(
        fn=translation,
        title="OpenAI-Translator v2.0(PDF 电子书翻译工具)",
        inputs=[
            gr.File(label="上传PDF文件"),
            gr.Dropdown(
                choices=available_models,
                value="glm-4",
                label="选择模型",
                info="选择要使用的大语言模型"
            ),
            gr.Textbox(
                label="ZhipuAI API密钥 (仅ChatGLM模型需要)",
                placeholder="sk-...",
                type="password"
            ),
            gr.Textbox(label="源语言（默认：英文）", placeholder="English", value="English"),
            gr.Textbox(label="目标语言（默认：中文）", placeholder="Chinese", value="Chinese"),
            gr.Dropdown(
                choices=translation_styles,
                value="standard",
                label="翻译风格",
                info="选择翻译的风格，如标准、小说、新闻稿等"
            )
        ],
        outputs=[
            gr.File(label="下载翻译文件")
        ],
        allow_flagging="never"
    )

    iface.launch(share=True, server_name="0.0.0.0")

def initialize_translator():
    # 解析命令行
    argument_parser = ArgumentParser()
    args = argument_parser.parse_arguments()

    # 初始化配置单例
    config = TranslationConfig()
    config.initialize(args)    
    
    # 检查是否有ChatGLM API密钥参数
    if hasattr(args, 'zhipuai_api_key') and args.zhipuai_api_key:
        os.environ['ZHIPUAI_API_KEY'] = args.zhipuai_api_key
        LOG.info("ZHIPUAI_API_KEY environment variable has been set")
    
    # 不再全局初始化翻译器，而是在每次调用时根据选择的模型创建


if __name__ == "__main__":
    # 初始化配置
    initialize_translator()
    # 启动 Gradio 服务
    launch_gradio()
