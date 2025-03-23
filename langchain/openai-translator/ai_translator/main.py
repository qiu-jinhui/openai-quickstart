import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import ArgumentParser, LOG
from translator import PDFTranslator, TranslationConfig

if __name__ == "__main__":
    # 解析命令行
    argument_parser = ArgumentParser()
    args = argument_parser.parse_arguments()

    # 如果提供了ChatGLM API密钥，则设置环境变量
    if hasattr(args, 'zhipuai_api_key') and args.zhipuai_api_key:
        os.environ['ZHIPUAI_API_KEY'] = args.zhipuai_api_key
        LOG.info("ZHIPUAI_API_KEY environment variable has been set")

    # 初始化配置单例
    config = TranslationConfig()
    config.initialize(args)    

    # 实例化 PDFTranslator 类，并调用 translate_pdf() 方法
    translator = PDFTranslator(config.model_name)
    translator.translate_pdf(config.input_file, config.output_file_format, pages=None)
