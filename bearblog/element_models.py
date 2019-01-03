from collections import namedtuple

Plain = namedtuple('Plain', ['type', 'text'])
Hyperlink = namedtuple('Hyperlink', ['type', 'text', 'link'])
Datetime = namedtuple('Datetime', ['type', 'utc'])
Table = namedtuple('Table', ['type', 'head', 'rows'])
Tabs = namedtuple('Tabs', ['type', 'tabs', 'selected_tab'])
Pagination = namedtuple('Pagination', ['type', 'pagination', 'endpoint', 'fragment'])
Option = namedtuple('Option', ['type', 'text', 'value'])
Select = namedtuple('Select', ['type', 'name', 'options'])
