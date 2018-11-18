from flask import Blueprint
from . import signals

main = Blueprint('main', __name__)

from . import views
