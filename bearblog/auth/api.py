from flask import request, jsonify
from flask_jwt_extended import create_access_token

from bearblog.models import User
from bearblog import component_route


@component_route('/login', 'login', 'api', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    user = User.query.filter_by(username=username).first()
    if user.verify_password(password):
        access_token = create_access_token(identity=username)
        return {'accessToken': access_token}
    return jsonify({"msg": "Bad username or password"}), 401
