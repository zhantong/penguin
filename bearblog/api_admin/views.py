from flask_jwt_extended import jwt_required

from bearblog import current_component


@current_component.blueprint.before_request
@jwt_required
def before_request():
    pass
