from flask import Blueprint, url_for
from . import signals

main = Blueprint('main', __name__)

from . import views


@signals.navbar.connect
def navbar(sender, content):
    content['brand'] = 'Penguin'
    content['items'].append(('首页', url_for('main.index')))
