from blinker import signal

get_widget = signal('tag.get_widget')
set_widget = signal('tag.set_widget')
filter = signal('tag.filter')
custom_list_column = signal('tag.custom_list_column')
restore = signal('tag.restore')
