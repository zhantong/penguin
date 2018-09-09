from blinker import signal

comment_submitted = signal('comment_submitted')
restore = signal('comment.restore')
get_comment_show_info = signal('comment.get_comment_show_info')
