from blinker import signal

get_widget = signal('category.get_widget')
set_widget = signal('category.set_widget')
get_widget_list = signal('category.get_widget_list')
filter = signal('category.filter')
custom_list_column = signal('category.custom_list_column')
