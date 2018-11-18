from blinker import signal

comment_submitted = signal('comment_submitted')
restore = signal('comment.restore')
get_comment_show_info = signal('comment.get_comment_show_info')
get_rendered_comments = signal('comment.get_rendered_comments')
on_new_comment = signal('comment.on_new_comment')
get_widget_latest_comments = signal('comment.get_widget_latest_comments')
