from flask import request, Response

from bearblog import current_component, component_route
from .models import Settings
from bearblog.models import Signal
from bearblog.extensions import db

Signal = Signal(None)
Signal.set_default_scope(current_component.slug)


@component_route('/settings/<category>', 'get_settings', 'api_admin', methods=['GET'])
def get_settings(category):
    settings = Settings.query.filter_by(category=category).all()
    return {'value': [setting.to_json() for setting in settings]}


@component_route('/settings/<int:id>', 'update_settings', 'api_admin', methods=['PATCH'])
def update_settings(id):
    setting = Settings.query.get(id)
    data = request.get_json()
    setting.value = data['rawValue']
    db.session.commit()
    return Response(status=200)
