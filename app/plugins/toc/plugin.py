from ..models import Plugin
from .models import Toc
from ...models import db

current_plugin = Plugin.current_plugin()


@current_plugin.signal.connect_this('get_widget')
def get_widget(sender, article, **kwargs):
    return {
        'slug': 'toc',
        'name': '文章目录',
        'html': current_plugin.render_template('widget_content_toc.html', article=article),
        'script': current_plugin.render_template('widget_script_toc.html'),
        'style': current_plugin.render_template('widget_style_toc.html')
    }


@Plugin.Signal.connect('article', 'markdown2_extra')
def markdown2_extra(sender, **kwargs):
    return 'toc'


@Plugin.Signal.connect('article', 'after_markdown_converted')
def after_markdown_converted(sender, article, html, **kwargs):
    toc = Toc(toc_html=html.toc_html, article=article)
    db.session.add(toc)
