from blinker import signal

article_list_column_head = signal('article_list_column_head')
article_list_column = signal('article_list_column')
article_search_select = signal('article_search_select')
edit_article = signal('edit_article')
submit_article = signal('submit_article')
submit_article_with_action = signal('submit_article_with_action')
article = signal('article')
restore_article = signal('restore_article')
article_list_url = signal('article_list_url')
custom_list = signal('article.custom_list')
list_column_head = signal('article.list_column_head')
list_column = signal('article.list_column')
