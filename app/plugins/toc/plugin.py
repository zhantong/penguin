import os.path
from ..article.signals import article


@article.connect
def article(sender, styles, left_widgets, scripts, **kwargs):
    styles.append(os.path.join('toc', 'templates', 'widget_style_toc.html'))
    left_widgets.append(os.path.join('toc', 'templates', 'widget_content_toc.html'))
    scripts.append(os.path.join('toc', 'templates', 'widget_script_toc.html'))
