import os
import os.path
from flask import Blueprint
from pathlib import Path

plugin = Blueprint('plugin', __name__)


def load_plugins():
    dirname = os.path.dirname(__file__)
    for name in os.listdir(dirname):
        if os.path.isdir(os.path.join(dirname, name)) and not name.startswith('.'):
            __import__(name, globals=globals(), fromlist=[name], level=1)


def add_template_file(file_list, caller_file_path, *paths):
    caller_file_path = caller_file_path.relative_to(Path(os.path.dirname(os.path.realpath(__file__))))
    plugin_dir_name = caller_file_path.parts[0]
    template_file_path = Path(plugin_dir_name, *paths).as_posix()
    file_list.append(template_file_path)
