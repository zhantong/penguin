from flask import render_template
from ..models import Plugin

toc = Plugin('文章目录', 'toc')
toc_instance = toc

toc_instance.signal.declare_signal('get_widget', return_type='single')


@toc_instance.signal.connect_this('get_widget')
def get_widget(sender, article, **kwargs):
    return {
        'slug': 'toc',
        'name': '文章目录',
        'html': render_template(toc_instance.template_path('widget_content_toc.html'), article=article),
        'script': render_template(toc_instance.template_path('widget_script_toc.html')),
        'style': render_template(toc_instance.template_path('widget_style_toc.html'))
    }
