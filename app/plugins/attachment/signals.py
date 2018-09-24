from blinker import signal

restore = signal('attachment.restore')
get_widget = signal('attachment.get_widget')
on_new_attachment = signal('on_new_attachment')
