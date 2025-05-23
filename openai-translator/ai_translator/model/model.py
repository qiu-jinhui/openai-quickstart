from book import ContentType

class Model:
    def make_text_prompt(self, text: str, target_language: str) -> str:
        return f"翻译为{target_language}, 仅仅对文字部分进行翻译，其他格式务必严格保持, 不需要返回其他信息：{text}"

    def make_table_prompt(self, table: str, target_language: str) -> str:
        # return f"翻译为{target_language}，保持间距（空格，分隔符），以表格形式返回：\n{table}"
        return f"翻译为{target_language}，仅仅对文字部分进行翻译，其他格式务必严格保持, 不需要返回其他信息：\n{table}"

    def translate_prompt(self, content, target_language: str) -> str:
        if content.content_type == ContentType.TEXT:
            return self.make_text_prompt(content.original, target_language)
        elif content.content_type == ContentType.TABLE:
            return self.make_table_prompt(content.get_original_as_str(), target_language)

    def make_request(self, prompt):
        raise NotImplementedError("子类必须实现 make_request 方法")
