from flask import Blueprint

main = Blueprint('main', __name__)

from ..plugins.models import Plugin

p = Plugin('main', 'main', show_in_sidebar=False)

from . import views
