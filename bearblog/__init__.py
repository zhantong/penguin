import json
import os
from io import BytesIO
from urllib.request import urlopen
from zipfile import ZipFile

import click
import flask_whooshalchemyplus
import jinja2
import redis
from flask import Flask
from rq import Connection, Worker

from bearblog.extensions import db
from bearblog.models import Role
from config import config
from ._globals import *
from .extensions import bootstrap, db, login_manager, csrf, moment
from .models import Component, Signal

_current_component = Component('bearblog', 'bearblog', show_in_sidebar=False)

_current_component.signal.declare_signal('context_processor', return_type='list')

Signal = Signal(None)
Signal.set_default_scope(_current_component.slug)


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    register_extensions(app)
    register_components(app)
    register_commands(app)
    register_template_context(app)

    Signal.send('create_app', 'bearblog', app=app)

    flask_whooshalchemyplus.init_app(app)

    return app


def register_extensions(app):
    bootstrap.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    moment.init_app(app)


def register_template_context(app):
    @app.template_test('list')
    def test_list(l):
        return isinstance(l, list)

    @app.template_filter('type')
    def filter_type(t):
        return type(t)

    app.jinja_loader = jinja2.ChoiceLoader([
        app.jinja_loader,
        jinja2.FileSystemLoader(['bearblog/plugins']),
        jinja2.FileSystemLoader(['bearblog'])
    ])

    @app.context_processor
    def context_processor():
        from .plugins.models import Plugin
        funcs = {
            'get_setting': Plugin.get_setting,
            'get_setting_value': Plugin.get_setting_value,
            'component_url_for': Component.view_url_for
        }
        for item in Signal.send('context_processor'):
            funcs.update(item)
        return funcs


def register_components(app):
    def load_components():
        pre_load_components()
        dirname = os.path.dirname(__file__)
        for name in os.listdir(dirname):
            if os.path.isdir(os.path.join(dirname, name)) and not name.startswith('.'):
                __import__(name, globals=globals(), fromlist=[name], level=1)

        for name in os.listdir(dirname):
            config_file = os.path.join(dirname, name, 'component.json')
            if os.path.isfile(config_file):
                with open(config_file) as f:
                    config = json.loads(f.read())
                component = Component.find_component(config['id'])
                component.done_setup(app)

    def pre_load_components():
        dirname = os.path.dirname(__file__)
        for name in os.listdir(dirname):
            config_file = os.path.join(dirname, name, 'component.json')
            if os.path.isfile(config_file):
                with open(config_file) as f:
                    config = json.loads(f.read())
                component = Component(config['name'], name, config['id'], show_in_sidebar=config['show_in_sidebar'], config=config)
                if 'signals' in config:
                    for signal in config['signals']:
                        name = signal.pop('name')
                        component.signal.declare_signal(name, **signal)
                component.setup(app)

    load_components()


def register_commands(app):
    @app.cli.command()
    def deploy():
        db.create_all()

        Role.insert_roles()

        Signal.send('deploy')

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

        download_js_package(os.path.abspath('bearblog/static/package.json'))

        for name in os.listdir('bearblog/plugins/'):
            config_file_path = os.path.abspath(os.path.join('bearblog', 'plugins', name, 'static', 'package.json'))
            if os.path.exists(config_file_path):
                download_js_package(config_file_path)

    @app.cli.command()
    def show_signals():
        signals = Signal._signals
        for signal, value in signals.items():
            print(signal)
            for name, value in value.items():
                print('\t', name)
                for item in value:
                    print('\t', '\t', item)

    @app.cli.command()
    def run_worker():
        redis_url = app.config['REDIS_URL']
        redis_connection = redis.from_url(redis_url)
        with Connection(redis_connection):
            worker = Worker(app.config['QUEUES'])
            worker.work()
