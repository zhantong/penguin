from ..article.signals import article
from ...plugins import add_template_file
from pathlib import Path
from ..article import signals as article_signals
from flask import render_template
import os.path


@article_signals.show.connect
def article_show(sender, article, left_widgets, scripts, styles, **kwargs):
    left_widgets.append(render_template(os.path.join('toc', 'templates', 'widget_content_toc.html'), article=article))
    scripts.append(render_template(os.path.join('toc', 'templates', 'widget_script_toc.html')))
    styles.append(render_template(os.path.join('toc', 'templates', 'widget_style_toc.html')))
