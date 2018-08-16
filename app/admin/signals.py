from blinker import signal

sidebar = signal('sidebar')
edit = signal('edit')
submit = signal('submit')
show_list = signal('show_list')
manage = signal('manage')
dispatch = signal('dispatch')
