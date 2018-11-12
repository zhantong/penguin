from blinker import signal

edit = signal('edit')
submit = signal('submit')
show_list = signal('show_list')
manage = signal('manage')
dispatch = signal('dispatch')
new_sidebar = signal('admin.sidebar')
