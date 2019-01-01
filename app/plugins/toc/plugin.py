from ..models import Plugin
from .. import plugin
from flask import send_from_directory
import os
from ...models import Signal

current_plugin = Plugin.current_plugin()


@plugin.route('/toc/static/<path:filename>')
def toc_static(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)


@Signal.connect('article', 'show_article_widget')
def show_article_widget(article, **kwargs):
    return {
        'slug': 'toc',
        'name': '文章目录',
        'html': current_plugin.render_template('widget_content_toc.html', article=article),
        'script': current_plugin.render_template('widget_script_toc.html'),
        'style': current_plugin.render_template('widget_style_toc.html')
    }
