import os
import os.path
from flask import Blueprint
import json
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
                    plugin.signal.declare_signal(signal['name'], signal['return_type'])
