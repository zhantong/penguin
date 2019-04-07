from bearblog import component_route
from .models import Template
from bearblog.plugins import current_plugin
from bearblog.models import Signal

Signal = Signal(None)
Signal.set_default_scope(current_plugin.slug)


@component_route('/templates', 'get_templates', 'api_admin')
def get_templates():
    return {
        'value': [{'id': template.id, 'name': template.name} for template in Template.query.all()]
    }
