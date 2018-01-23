import os
import os.path


def load_plugins():
    for name in os.listdir(os.path.dirname(__file__)):
        if not name.startswith('__'):
            plugin = __import__('app.plugins.' + name, fromlist=[name])
