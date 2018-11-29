import os
import os.path
from flask import Blueprint

plugin = Blueprint('plugin', __name__)


def load_plugins():
    dirname = os.path.dirname(__file__)
    for name in os.listdir(dirname):
        if os.path.isdir(os.path.join(dirname, name)) and not name.startswith('.'):
            __import__(name, globals=globals(), fromlist=[name], level=1)
