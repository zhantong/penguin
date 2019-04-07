from flask_jwt_extended import get_jwt_identity

from bearblog import component_route
from bearblog.models import User


@component_route('/me', 'get_me', 'api_admin')
def get_me():
    current_username = get_jwt_identity()
    user = User.query.filter_by(username=current_username).first()
    return user.to_json('admin_brief')
