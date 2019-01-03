import os

from flask import send_from_directory

from bearblog.plugins import current_plugin, plugin
from bearblog.models import Signal


@plugin.route('/toc/static/<path:filename>')
def toc_static(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)


@Signal.connect('article', 'show_article_widget')
def show_article_widget(article):
    return {
        'slug': 'toc',
        'name': '文章目录',
        'html': current_plugin.render_template('widget_content_toc.html', article=article),
        'script': current_plugin.render_template('widget_script_toc.html'),
        'style': current_plugin.render_template('widget_style_toc.html')
    }