import pdfplumber
from typing import Optional, List, Dict, Any
from book import Book, Page, Content, ContentType, ElementType, TableContent
from translator.exceptions import PageOutOfRangeException
from utils import LOG

def extract_text_elements(pdf_page):
    """提取并分类文本元素（标题和段落）"""
    # 提取所有文本元素
    chars = pdf_page.chars
    
    # 按字体大小和样式分组
    text_elements = []
    current_line = []
    last_y = None

    tables = pdf_page.extract_tables()
    
    # 对字符按y坐标排序，确保从上到下处理
    sorted_chars = sorted(chars, key=lambda x: -x['top'])
    
    for char in sorted_chars:
        if last_y is None:
            current_line.append(char)
        else:
            # 如果y坐标差异小于字体大小的一半，认为是同一行
            if abs(char['top'] - last_y) < char['size'] * 0.5:
                current_line.append(char)
            else:
                # 处理当前行
                if current_line:
                    line_info = process_line(current_line, tables)
                    if line_info is not None:
                        text_elements.append(line_info)
                current_line = [char]
        last_y = char['top']
    
    # 处理最后一行
    if current_line:
        line_info = process_line(current_line, tables)
        if line_info is not None:
            text_elements.append(line_info)
    
    # 识别标题和段落
    elements = classify_elements(text_elements)
    return elements

def process_line(chars: List[Dict], tables: List[List[str]]) -> Dict:
    
    text = ''.join(c['text'] for c in chars)
    # TODO 如果text中包含tables里面的text，则将text中的tables里面的text删除
    for table in tables:
        for row in table:
            for cell in row:
                if cell in text:
                    text = text.replace(cell, '')

    if (len(text.strip()) == 0):
        return None
    
    """处理单行文本，提取布局信息"""
    return {
        'text': text,
        'position': {
            'x0': min(c['x0'] for c in chars),
            'x1': max(c['x1'] for c in chars),
            'y0': min(c['top'] for c in chars),
            'y1': max(c['bottom'] for c in chars)
        },
        'font': chars[0]['fontname'],
        'size': chars[0]['size'],
        'chars': chars  # 保留原始字符信息
    }

def classify_elements(text_elements: List[Dict]) -> List[Dict]:

    if len(text_elements) == 0:
        return []

    """将文本元素分类为标题和段落"""
    # 计算字体大小的分布
    sizes = [elem['size'] for elem in text_elements]
    avg_size = sum(sizes) / len(sizes)
    
    classified = []
    for elem in text_elements:
        # 判断是否为标题
        is_title = (
            elem['size'] > avg_size * 1.2 or  # 字体显著大于平均值
            elem['font'].lower().find('bold') >= 0 or  # 粗体
            all(c.isupper() for c in elem['text'] if c.isalpha())  # 全大写
        )
        
        elem['type'] = ElementType.TITLE if is_title else ElementType.PARAGRAPH
        classified.append(elem)
    
    return classified

def extract_table_with_layout_bak(pdf_page) -> List[Dict]:
    """提取表格及其布局信息"""
    # 提取表格
    tables = pdf_page.extract_tables()
    table_layouts = []
    
    # 获取页面上的所有线条
    h_lines = pdf_page.horizontal_edges
    v_lines = pdf_page.vertical_edges
    
    for table in tables:
        # 找到表格的边界
        table_chars = []
        for row in table:
            for cell in row:
                if cell:
                    cell_chars = [
                        c for c in pdf_page.chars
                        if c['text'] in cell
                    ]
                    table_chars.extend(cell_chars)
        
        if not table_chars:
            continue
            
        # 计算表格边界
        table_bbox = {
            'x0': min(c['x0'] for c in table_chars),
            'x1': max(c['x1'] for c in table_chars),
            'y0': min(c['top'] for c in table_chars),
            'y1': max(c['bottom'] for c in table_chars)
        }
        
        # 查找表格线条
        table_h_lines = [
            line for line in h_lines
            if (line['x0'] >= table_bbox['x0'] - 5 and
                line['x1'] <= table_bbox['x1'] + 5)
        ]
        
        table_v_lines = [
            line for line in v_lines
            if (line['y0'] >= table_bbox['y0'] - 5 and
                line['y1'] <= table_bbox['y1'] + 5)
        ]
        
        # 构建单元格布局信息
        cells_layout = []
        for i, row in enumerate(table):
            for j, cell in enumerate(row):
                if cell:
                    cell_chars = [
                        c for c in pdf_page.chars
                        if c['text'] in cell
                    ]
                    if cell_chars:
                        cell_info = {
                            'text': cell,
                            'position': {
                                'x0': min(c['x0'] for c in cell_chars),
                                'x1': max(c['x1'] for c in cell_chars),
                                'y0': min(c['top'] for c in cell_chars),
                                'y1': max(c['bottom'] for c in cell_chars)
                            },
                            'font': cell_chars[0]['fontname'],
                            'size': cell_chars[0]['size'],
                            'row': i,
                            'col': j
                        }
                        cells_layout.append(cell_info)
        
        table_layouts.append({
            'cells': cells_layout,
            'bbox': table_bbox,
            'h_lines': table_h_lines,
            'v_lines': table_v_lines
        })
    
    return table_layouts

def extract_table_with_layout(pdf_page) -> List[Dict]:
    """提取表格及其布局信息"""
    # 提取表格
    tables = pdf_page.extract_tables()
    tables_debugger = pdf_page.debug_tablefinder()

    table_layouts = []
    
    # 获取页面上的所有线条
    h_lines = pdf_page.horizontal_edges
    v_lines = pdf_page.vertical_edges
    
    for index, table in enumerate(tables):
        # 找到表格的边界
        table_chars = []
        for row in table:
            for cell in row:
                if cell:
                    cell_chars = [
                        c for c in pdf_page.chars
                        if c['text'] in cell
                    ]
                    table_chars.extend(cell_chars)
        
        if not table_chars:
            continue
            
        # 计算表格边界
        table_bbox = {
            'x0': min(c['x0'] for c in table_chars),
            'x1': max(c['x1'] for c in table_chars),
            'y0': min(c['top'] for c in table_chars),
            'y1': max(c['bottom'] for c in table_chars)
        }
        
        # 查找表格线条
        table_h_lines = [
            line for line in h_lines
            if (line['x0'] >= table_bbox['x0'] - 5 and
                line['x1'] <= table_bbox['x1'] + 5)
        ]
        
        table_v_lines = [
            line for line in v_lines
            if (line['y0'] >= table_bbox['y0'] - 5 and
                line['y1'] <= table_bbox['y1'] + 5)
        ]
        
        # 查找表格线条
        table_h_lines = [
            line for line in h_lines
            if (line['x0'] >= table_bbox['x0'] - 5 and
                line['x1'] <= table_bbox['x1'] + 5)
        ]
        
        table_v_lines = [
            line for line in v_lines
            if (line['y0'] >= table_bbox['y0'] - 5 and
                line['y1'] <= table_bbox['y1'] + 5)
        ]
        
        # 构建单元格布局信息
        cells_layout = []
        for i, row in enumerate(table):
            for j, cell in enumerate(row):
                if cell:
                    cell_chars = [
                        c for c in pdf_page.chars
                        if c['text'] in cell
                    ]
                    if cell_chars:
                        cell_info = {
                            'text': cell,
                            'position': {
                                'x0': tables_debugger.tables[index].rows[i].cells[j][0],
                                'x1': tables_debugger.tables[index].rows[i].cells[j][1],
                                'y0': tables_debugger.tables[index].rows[i].cells[j][2],
                                'y1': tables_debugger.tables[index].rows[i].cells[j][3]
                            },
                            'font': cell_chars[0]['fontname'],
                            'size': cell_chars[0]['size'],
                            'row': i,
                            'col': j
                        }
                        cells_layout.append(cell_info)
        
        table_layouts.append({
            'cells': cells_layout,
            'bbox': table_bbox,
            'h_lines': table_h_lines,
            'v_lines': table_v_lines
        })
    
    return table_layouts

class PDFParser:
    def __init__(self):
        pass

    def parse_pdf(self, pdf_file_path: str, pages: Optional[int] = None) -> Book:
        """解析PDF文件，保留布局信息"""
        book = Book(pdf_file_path)
        
        with pdfplumber.open(pdf_file_path) as pdf:
            if pages is not None and pages > len(pdf.pages):
                raise PageOutOfRangeException(len(pdf.pages), pages)
            
            pages_to_parse = pdf.pages[:pages] if pages else pdf.pages
            
            for pdf_page in pages_to_parse:
                page = Page(pdf_page.width, pdf_page.height)
                
                # 1. 提取文本元素（标题和段落）
                text_elements = extract_text_elements(pdf_page)
                for elem in text_elements:
                    content = Content(
                        content_type=ContentType.TEXT,
                        element_type=elem['type'],
                        original=elem['text'],
                        position=elem['position'],
                        font=elem['font'],
                        font_size=elem['size']
                    )
                    page.add_content(content)
                
                # 2. 提取表格
                tables = extract_table_with_layout(pdf_page)
                for table in tables:
                    table_content = TableContent(
                        original=table['cells'],
                        position=table['bbox'],
                        borders={
                            'horizontal': table['h_lines'],
                            'vertical': table['v_lines']
                        }
                    )
                    page.add_content(table_content)
                
                book.add_page(page)
                #LOG.debug(f"Processed page with {len(text_elements)} text elements and {len(tables)} tables")
        
        return book
