import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

from app import create_app, db
from app.plugins.post.models import PostStatus
from app.models import Role
import click
import json
from io import BytesIO
from zipfile import ZipFile
from urllib.request import urlopen

app = create_app(os.environ.get('FLASK_CONFIG', 'default'))


@app.cli.command()
def deploy():
    db.create_all()

    Role.insert_roles()
    PostStatus.insert_post_statuses()


@app.cli.command()
@click.option('--file-path', default=None, help='dumped file path')
def restore(file_path):
    from migrations.Restore import Restore
    Restore(file_path).restore()


@app.cli.command()
def download_js_packages():
    def download_js_package(config_file_path):
        with open(config_file_path, 'r') as f:
            config = json.loads(f.read())
        for name, url in config.items():
            print(name, url)
            with urlopen(url) as resp:
                with ZipFile(BytesIO(resp.read())) as zipfile:
                    zipfile.extractall(os.path.dirname(config_file_path))

    download_js_package(os.path.abspath('app/static/package.json'))

    for name in os.listdir('app/plugins/'):
        config_file_path = os.path.abspath(os.path.join('app/plugins', name, 'static', 'package.json'))
        if os.path.exists(config_file_path):
            download_js_package(config_file_path)


@app.cli.command()
def show_signals():
    import blinker
    import inspect
    signals = blinker.signal.__self__
    for name, signal in sorted(signals.items()):
        print(name)
        for func in signal.receivers.values():
            func_type = type(func)
            if func_type is blinker._utilities.annotatable_weakref:
                func = func()
            print('\t', 'name: ', func.__name__, 'signature: ', inspect.signature(func), 'file: ',
                  inspect.getsourcefile(func), 'line: ', func.__code__.co_firstlineno)
