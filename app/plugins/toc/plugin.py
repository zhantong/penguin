from flask import render_template
from ..models import Plugin

current_plugin = Plugin.current_plugin()

current_plugin.signal.declare_signal('get_widget', return_type='single')


@current_plugin.signal.connect_this('get_widget')
def get_widget(sender, article, **kwargs):
    return {
        'slug': 'toc',
        'name': '文章目录',
        'html': render_template(current_plugin.template_path('widget_content_toc.html'), article=article),
        'script': render_template(current_plugin.template_path('widget_script_toc.html')),
        'style': render_template(current_plugin.template_path('widget_style_toc.html'))
    }
