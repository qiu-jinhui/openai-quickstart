from .content import Content

class Page:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.contents = []

    def add_content(self, content: Content):
        self.contents.append(content)
