from bearblog import component_route
from .models import Tag
from bearblog.plugins import current_plugin
from bearblog.models import Signal

Signal = Signal(None)
Signal.set_default_scope(current_plugin.slug)


@component_route('/admin/tags', 'get_tags', 'api')
def get_tags():
    return {
        'value': [tag.name for tag in Tag.query.all()]
    }
