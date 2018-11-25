from blinker import signal

show = signal('page.show')
custom_list = signal('page.custom_list')
get_navbar_item = signal('page.get_navbar_item')
get_admin_page_list = signal('page.get_admin_page_list')
filter = signal('page.filter')
dynamic_page = signal('page.dynamic_page')
