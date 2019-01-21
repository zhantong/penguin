import json
import os
import os.path

from . import views
from ._globals import *
from .models import Plugin


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
            plugin = Plugin(config['name'], os.path.join(dirname, name), config['id'], show_in_sidebar=config['show_in_sidebar'], config=config)
            if 'signals' in config:
                for signal in config['signals']:
                    name = signal.pop('name')
                    plugin.signal.declare_signal(name, **signal)


load_plugins()
