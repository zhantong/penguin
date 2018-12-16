from ..models import Plugin

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
