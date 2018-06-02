from blinker import signal

post_keywords = signal('post_keywords')
create_post = signal('create_post')
update_post = signal('update_post')
custom_list = signal('custom_list')
post_list_column_head = signal('post_list_column_head')
post_list_column = signal('post_list_column')
post_search_select = signal('post_search_select')
edit_post = signal('edit_post')
