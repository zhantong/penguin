from blinker import signal

edit_page = signal('edit_page')
submit_page = signal('submit_page')
submit_page_with_action = signal('submit_page_with_action')
page = signal('page')
restore = signal('page.restore')
show = signal('page.show')
custom_list = signal('page.custom_list')
get_navbar_item = signal('page.get_navbar_item')
