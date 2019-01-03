import json
import os
import os.path

from flask import Blueprint

from . import views
from ._globals import *
from .models import Plugin

plugin = Blueprint('plugin', __name__)


def load_plugins():
    pre_load_plugins()
    dirname = os.path.dirname(__file__)
    for name in os.listdir(dirname):
        if os.path.isdir(os.path.join(dirname, name)) and not name.startswith('.'):
            __import__(name, globals=globals(), fromlist=[name], level=1)


def pre_load_plugins():
    dirname = os.path.dirname(__file__)
    for name in os.listdir(dirname):
        config_file = os.path.join(dirname, name, 'plugin.json')
        if os.path.isfile(config_file):
            with open(config_file) as f:
                config = json.loads(f.read())
            plugin = Plugin(config['name'], name, config['id'], show_in_sidebar=config['show_in_sidebar'])
            if 'signals' in config:
                for signal in config['signals']:
                    name = signal.pop('name')
                    plugin.signal.declare_signal(name, **signal)


load_plugins()