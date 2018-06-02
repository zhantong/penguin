from flask import Blueprint, url_for
from . import signals
from ..signals import navbar

main = Blueprint('main', __name__)

from . import views


@navbar.connect
def navbar(sender, content):
    content['brand'] = 'Penguin'
    content['items'].append(('首页', url_for('main.index')))
