from blinker import signal
from ...models import db, Attachment
import os.path

edit_article = signal('edit_article')


@edit_article.connect
def edit_article(sender, args, context, styles, hiddens, contents, widgets, scripts):
    context['attachments'] = Attachment.query.filter_by(post_id=context['post'].id).all()
    widgets.append(os.path.join('attachment', 'templates', 'widget_content_attachment.html'))
    widgets.append(os.path.join('attachment', 'templates', 'widget_script_attachment.html'))
