import pandas as pd
from enum import Enum, auto
from PIL import Image as PILImage
from typing import Dict, Any, Optional
from utils import LOG
import io
class ContentType(Enum):
    TEXT = auto()
    TABLE = auto()
    IMAGE = auto()

class ElementType(Enum):
    TITLE = auto()
    PARAGRAPH = auto()
    TABLE = auto()
    IMAGE = auto()

class Content:
    def __init__(self, 
                 content_type: ContentType,
                 element_type: ElementType,
                 original: Any,
                 position: Dict[str, float],
                 font: str = None,
                 font_size: float = None,
                 style: Dict[str, Any] = None,
                 translation: Any = None):
        self.content_type = content_type
        self.element_type = element_type
        self.original = original
        self.translation = translation
        self.position = position
        self.font = font
        self.font_size = font_size
        self.style = style or {}
        self.status = False

    def set_translation(self, translation, status):
        if not self.check_translation_type(translation):
            raise ValueError(f"Invalid translation type. Expected {self.content_type}, but got {type(translation)}")
        self.translation = translation
        self.status = status

    def check_translation_type(self, translation):
        if self.content_type == ContentType.TEXT and isinstance(translation, str):
            return True
        elif self.content_type == ContentType.TABLE and isinstance(translation, pd.DataFrame):
            return True
        elif self.content_type == ContentType.IMAGE and isinstance(translation, PILImage.Image):
            return True
        return False


class TableContent(Content):
    def __init__(self, original: Any, position: Dict[str, float], borders: Dict = None, translation: Any = None):
        super().__init__(
            content_type=ContentType.TABLE,
            element_type=ElementType.TABLE,
            original=original,
            position=position,
            translation=translation
        )
        self.borders = borders or {'horizontal': [], 'vertical': []}
        
        # Convert table data to DataFrame if it's not already
        if isinstance(original, list):
            self.original = pd.DataFrame(original)

    def set_translation(self, translation, status):
        try:
            if not isinstance(translation, str):
                raise ValueError(f"Invalid translation type. Expected str, but got {type(translation)}")

            LOG.debug(translation)
            # Convert the string to a list of lists
            # table_data = [row.strip().split() for row in translation.strip().split('\n')]
            # table_data = "\n".join(translation.strip().split("\n"))
            # LOG.debug(table_data)
            # Create a DataFrame from the table_data
            # translated_df = pd.DataFrame(table_data[1:], columns=table_data[0])
            translated_df = pd.df = pd.read_csv(io.StringIO(translation), header=None, names=['text', 'col', 'row'])
            LOG.debug(translated_df)
            self.translation = translated_df
            self.status = status
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
        # 将dataframe对象转成markdown格式，忽略header和index，只包含text, col, row字段
        return self.original[['text', 'col', 'row']].to_csv(header=False, index=False)