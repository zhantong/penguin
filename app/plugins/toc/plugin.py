from ..article.signals import article
from ...plugins import add_template_file
from pathlib import Path


@article.connect
def article(sender, styles, left_widgets, scripts, **kwargs):
    add_template_file(styles, Path(__file__), 'templates', 'widget_style_toc.html')
    add_template_file(left_widgets, Path(__file__), 'templates', 'widget_content_toc.html')
    add_template_file(scripts, Path(__file__), 'templates', 'widget_script_toc.html')
