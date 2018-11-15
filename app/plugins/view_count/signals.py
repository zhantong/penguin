from blinker import signal

viewing = signal('view_count.viewing')
get_count = signal('view_count.get_count')
restore = signal('view_count.restore')
