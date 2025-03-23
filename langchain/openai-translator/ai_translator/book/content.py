import pandas as pd

from enum import Enum, auto
from PIL import Image as PILImage
from utils import LOG
from io import StringIO

class ContentType(Enum):
    TEXT = auto()
    TABLE = auto()
    IMAGE = auto()

class Content:
    def __init__(self, content_type, original, translation=None):
        self.content_type = content_type
        self.original = original
        self.translation = translation
        self.status = False

    def set_translation(self, translation, status):
        if not self.check_translation_type(translation):
            raise ValueError(f"Invalid translation type. Expected {self.content_type}, but got {type(translation)}")
        
        # 如果是文本类型且是字符串类型，处理可能的前缀
        if self.content_type == ContentType.TEXT and isinstance(translation, str):
            # 移除常见的模型响应前缀
            prefixes = [
                "Here is the translation of the provided text into Chinese:",
                "Translation:",
                "翻译:",
                "翻译结果：",
                "译文："
            ]
            for prefix in prefixes:
                if translation.startswith(prefix):
                    translation = translation[len(prefix):].strip()
        
        self.translation = translation
        self.status = status

    def check_translation_type(self, translation):
        if self.content_type == ContentType.TEXT and isinstance(translation, str):
            return True
        elif self.content_type == ContentType.TABLE and isinstance(translation, list):
            return True
        elif self.content_type == ContentType.IMAGE and isinstance(translation, PILImage.Image):
            return True
        return False

    def __str__(self):
        return self.original


class TableContent(Content):
    def __init__(self, data, translation=None):
        df = pd.DataFrame(data)

        # Verify if the number of rows and columns in the data and DataFrame object match
        if len(data) != len(df) or len(data[0]) != len(df.columns):
            raise ValueError("The number of rows and columns in the extracted table data and DataFrame object do not match.")
        
        super().__init__(ContentType.TABLE, df)

    def set_translation(self, translation, status):
        try:
            if not isinstance(translation, str):
                raise ValueError(f"Invalid translation type. Expected str, but got {type(translation)}")

            LOG.debug(f"[translation]\n{translation}")
            
            # 移除常见的模型响应前缀
            prefixes = [
                "Here is the translation of the provided text into Chinese:",
                "Translation:",
                "翻译:",
                "翻译结果：",
                "译文："
            ]
            for prefix in prefixes:
                if translation.startswith(prefix):
                    translation = translation[len(prefix):].strip()
            
            # 检查结果是否包含表格数据
            if "[" not in translation or "]" not in translation:
                LOG.error("Translation result does not contain valid table data")
                self.translation = None
                self.status = False
                return
                
            # 提取表格数据
            try:
                # 尝试提取第一个中括号中的内容作为表头
                header_start = translation.find("[")
                header_end = translation.find("]", header_start)
                header_text = translation[header_start+1:header_end]
                
                # 处理表头，分隔符可能是逗号或空格
                if "," in header_text:
                    header = [x.strip() for x in header_text.split(",")]
                else:
                    header = [x.strip() for x in header_text.split() if x.strip()]
                
                # 提取每一行数据
                data_rows = []
                current_pos = header_end + 1
                
                while True:
                    row_start = translation.find("[", current_pos)
                    if row_start == -1:
                        break
                        
                    row_end = translation.find("]", row_start)
                    if row_end == -1:
                        break
                        
                    row_text = translation[row_start+1:row_end]
                    
                    # 处理行数据，分隔符可能是逗号或空格
                    if "," in row_text:
                        row_data = [x.strip() for x in row_text.split(",")]
                    else:
                        row_data = [x.strip() for x in row_text.split() if x.strip()]
                    
                    data_rows.append(row_data)
                    current_pos = row_end + 1
                
                # 检查是否有足够的数据
                if not data_rows:
                    raise ValueError("No data rows found in the translation")
                
                # 确保所有行有相同数量的列
                max_cols = max(len(row) for row in data_rows)
                for i, row in enumerate(data_rows):
                    if len(row) < max_cols:
                        data_rows[i].extend([''] * (max_cols - len(row)))
                
                # 确保header有足够的列
                if len(header) < max_cols:
                    header.extend([f'Column {i+1}' for i in range(len(header), max_cols)])
                
                # 创建DataFrame
                translated_df = pd.DataFrame(data_rows, columns=header)
                
                # 清理数据：移除表格统计或元数据行
                # 如果有任何行包含"行x"或"列"等词语，可能是表格的元数据信息，应该移除
                rows_to_drop = []
                for idx, row in translated_df.iterrows():
                    row_data = ' '.join(str(x) for x in row.values)
                    if any(x in row_data for x in ['行x', '列]', '行 x', 'rows', 'columns']):
                        rows_to_drop.append(idx)
                
                if rows_to_drop:
                    translated_df = translated_df.drop(rows_to_drop)
                
                LOG.debug(f"[translated_df]\n{translated_df}")
                
                self.translation = translated_df
                self.status = status
            except Exception as inner_e:
                LOG.error(f"Error parsing table data: {inner_e}")
                self.translation = None
                self.status = False
                
        except Exception as e:
            LOG.error(f"An error occurred during table translation: {e}")
            self.translation = None
            self.status = False

    def __str__(self):
        return self.original.to_string(header=False, index=False)

    def iter_items(self, translated=False):
        target_df = self.translation if translated else self.original
        for row_idx, row in target_df.iterrows():
            for col_idx, item in enumerate(row):
                yield (row_idx, col_idx, item)

    def update_item(self, row_idx, col_idx, new_value, translated=False):
        target_df = self.translation if translated else self.original
        target_df.at[row_idx, col_idx] = new_value

    def get_original_as_str(self):
        return self.original.to_string(header=False, index=False)