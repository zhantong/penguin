from flask import request, jsonify
from flask_jwt_extended import create_access_token, get_raw_jwt

from bearblog.models import User
from bearblog import component_route
from bearblog.extensions import jwt

blacklist = set()


@jwt.token_in_blacklist_loader
def check_if_token_in_blacklist(decrypted_token):
    jti = decrypted_token['jti']
    return jti in blacklist


@component_route('/login', 'login', 'api', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    user = User.query.filter_by(username=username).first()
    if user.verify_password(password):
        access_token = create_access_token(identity=username)
        return {'accessToken': access_token}
    return jsonify({"msg": "Bad username or password"}), 401


@component_route('/logout', 'logout', 'api_admin', methods=['DELETE'])
def logout():
    jti = get_raw_jwt()['jti']
    blacklist.add(jti)
    return {"msg": "Successfully logged out"}
