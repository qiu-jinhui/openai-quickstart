import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from book import Book, Content, ContentType, ElementType
from utils import LOG
import pandas as pd

class Writer:
    def __init__(self):
        # 注册中文字体
        font_path = "../fonts/simsun.ttc"  # 请将此路径替换为您的字体文件路径
        pdfmetrics.registerFont(TTFont('SimSun', font_path))

    def save_translated_book(self, book: Book, output_file_path: str = None, file_format: str = 'PDF'):
        """保存翻译后的内容到文件"""
        if output_file_path is None:
            output_file_path = self._generate_output_path(book.pdf_file_path, file_format)

        if file_format.upper() == 'PDF':
            self._save_as_pdf_with_layout(book, output_file_path)
        elif file_format.upper() == 'MARKDOWN':
            self._save_as_markdown(book, output_file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

        return output_file_path

    def _save_as_pdf_with_layout(self, book: Book, output_path: str):
        """保存为PDF，保持原始布局"""
        if len(book.pages) == 0:
            c = canvas.Canvas(output_path, pagesize=letter) # TODO pagesize 需要从pdf文件中获取
            page_height = letter[1]
        else:
            c = canvas.Canvas(output_path, pagesize=(book.pages[0].width, book.pages[0].height))
            page_height = book.pages[0].height

# PDF坐标系从底部开始

        for page in book.pages:
            # 按y坐标排序，确保从上到下绘制
            sorted_contents = sorted(
                page.contents,
                key=lambda x: x.position['y0'] if x.position else 0
            )

            for content in sorted_contents:
                if content.content_type == ContentType.TEXT:
                    # 转换坐标（pdfplumber和reportlab使用不同的坐标系）
                    y = page_height - content.position['y1']
                    
                    # 设置字体和大小
                    font_name = 'SimSun'  # 使用中文字体
                    font_size = content.font_size or 12
                    c.setFont(font_name, font_size)
                    
                    # 根据内容类型设置样式
                    if content.element_type == ElementType.TITLE:
                        c.setFont(font_name, font_size * 1.2)  # 标题字体放大
                    
                    # 绘制文本
                    text = content.translation if content.translation else content.original
                    c.drawString(
                        content.position['x0'],
                        y,
                        text
                    )
                
                elif content.content_type == ContentType.TABLE:
                    # 绘制表格边框
                    adjust = 112
                    if content.borders:
                        for line in content.borders.get('horizontal', []):
                            c.line(
                                line['x0'],
                                page_height - line['y0'] - adjust,
                                line['x1'],
                                page_height - line['y1'] - adjust
                            )
                        
                        for line in content.borders.get('vertical', []):
                            c.line(
                                line['x0'],
                                page_height - line['y0'] - adjust,
                                line['x1'],
                                page_height - line['y1'] - adjust
                            )
                    
                    # 绘制表格内容
                    if isinstance(content.original, pd.DataFrame):
                        for cell in content.original.itertuples():
                            c.setFont('SimSun', cell.size)
                            cell_text = cell.text
                            if content.translation is not None:
                                # 查找对应的翻译
                                cell_pos = (cell.row, cell.col)
                                for trans_cell in content.translation.itertuples():
                                    if (trans_cell.row, trans_cell.col) == cell_pos:
                                        cell_text = trans_cell.text
                                        break
                            
                            LOG.info(f"{cell_text}: {cell.position['x0']}, {page_height - cell.position['y1']}")
                            adjust = 10
                            c.drawString(
                                cell.position['x0'] + adjust,
                                page_height - cell.position['y1'],
                                cell_text
                            )
            
            c.showPage()
        
        c.save()
        LOG.info(f"Saved PDF with layout to {output_path}")

    def _save_as_markdown(self, book: Book, output_path: str):
        """保存为Markdown格式"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for page in book.pages:
                for content in page.contents:
                    if content.content_type == ContentType.TEXT:
                        if content.element_type == ElementType.TITLE:
                            f.write(f"# {content.translation or content.original}\n\n")
                        else:
                            f.write(f"{content.translation or content.original}\n\n")
                    
                    elif content.content_type == ContentType.TABLE:
                        # 创建markdown表格
                        if isinstance(content.original, list):
                            # 获取列数
                            max_cols = max(cell['col'] for cell in content.original) + 1
                            
                            # 写入表头分隔符
                            f.write('|' + '|'.join(['---'] * max_cols) + '|\n')
                            
                            # 按行写入单元格
                            current_row = -1
                            row_cells = []
                            for cell in sorted(content.original, key=lambda x: (x['row'], x['col'])):
                                if cell['row'] != current_row:
                                    if row_cells:
                                        f.write('|' + '|'.join(row_cells) + '|\n')
                                    current_row = cell['row']
                                    row_cells = [''] * max_cols
                                
                                cell_text = cell['text']
                                if content.translation:
                                    # 查找对应的翻译
                                    cell_pos = (cell['row'], cell['col'])
                                    for trans_cell in content.translation:
                                        if (trans_cell['row'], trans_cell['col']) == cell_pos:
                                            cell_text = trans_cell['text']
                                            break
                                
                                row_cells[cell['col']] = cell_text
                            
                            # 写入最后一行
                            if row_cells:
                                f.write('|' + '|'.join(row_cells) + '|\n')
                            
                            f.write('\n')
                
                f.write('---\n\n')  # 页面分隔符
        
        LOG.info(f"Saved Markdown to {output_path}")

    def _generate_output_path(self, input_path: str, file_format: str) -> str:
        """生成输出文件路径"""
        dir_name = os.path.dirname(input_path)
        file_name = os.path.basename(input_path)
        name, _ = os.path.splitext(file_name)
        
        if file_format.upper() == 'PDF':
            output_path = os.path.join(dir_name, f"{name}_translated.pdf")
        elif file_format.upper() == 'MARKDOWN':
            output_path = os.path.join(dir_name, f"{name}_translated.md")
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
        
        return output_path