from ..article import signals as article_signals
from flask import render_template
from ..models import Plugin

toc = Plugin('文章目录', 'toc')
toc_instance = toc


@article_signals.show.connect
def article_show(sender, article, left_widgets, scripts, styles, **kwargs):
    left_widgets.append(render_template(toc_instance.template_path('widget_content_toc.html'), article=article))
    scripts.append(render_template(toc_instance.template_path('widget_script_toc.html')))
    styles.append(render_template(toc_instance.template_path('widget_style_toc.html')))
