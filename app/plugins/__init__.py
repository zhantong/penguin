import os
import os.path
from flask import Blueprint

plugin = Blueprint('plugin', __name__)


def load_plugins():
    for name in os.listdir(os.path.dirname(__file__)):
        if not name.startswith('__') and not name.startswith('.'):
            __import__(name, globals=globals(), fromlist=[name], level=1)
