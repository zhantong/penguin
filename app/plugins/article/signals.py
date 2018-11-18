from blinker import signal

restore = signal('article.restore')
article_list_url = signal('article_list_url')
custom_list = signal('article.custom_list')
list_column_head = signal('article.list_column_head')
list_column = signal('article.list_column')
show_edit_article_widget = signal('article.show_edit_article_widget')
show = signal('article.show')
get_widget_category_list = signal('article.get_widget_category_list')
get_widget_article_list = signal('article.get_widget_article_list')
filter = signal('article.filter')
get_navbar_item = signal('article.get_navbar_item')
