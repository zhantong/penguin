from blinker import signal

edit_page = signal('edit_page')
submit_page = signal('submit_page')
submit_page_with_action = signal('submit_page_with_action')
page = signal('page')
restore_page=signal('restore_page')
