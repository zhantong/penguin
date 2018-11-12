from blinker import signal

get_widget = signal('template.get_widget')
set_widget = signal('template.set_widget')
render_template = signal('template.render_template')
