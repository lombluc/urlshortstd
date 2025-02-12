from html.parser import HTMLParser


class HTMLTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_th = False
        self.in_td = False
        self.column_names = []
        self.cur_index = 0
        self.table_data = {}

    def handle_starttag(self, tag, attrs):
        # print("Encountered a start tag:", tag)
        if tag == "table":
            self.in_table = True
            self.table_data = {}
        elif tag == "th":
            self.in_th = True
        elif tag == "td":
            self.in_td = True

    def handle_endtag(self, tag):
        # print("Encountered an end tag :", tag)
        if tag == "table":
            self.in_table = False
        elif tag == "th":
            self.in_th = False
        elif tag == "td":
            self.in_td = False
            self.cur_index += 1
        elif tag == "tr":
            self.cur_index = 0

    def handle_data(self, data):
        # print("Encountered some data  :", data)
        if not self.in_table:
            return
        if self.in_th:
            self.column_names.append(data)
            self.table_data[data] = []
        elif self.in_td:
            self.table_data[self.column_names[self.cur_index]].append(data)
