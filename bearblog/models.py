import inspect
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
import os.path

from flask import url_for, render_template, Blueprint, request
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.routing import Rule, Map

from .extensions import db, login_manager


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    users = db.relationship('User', back_populates='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = ('管理员', '访客')
        default_role = '访客'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()

    @staticmethod
    def admin():
        return Role.query.filter_by(name='管理员').first()

    @staticmethod
    def guest():
        return Role.query.filter_by(name='访客').first()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    name = db.Column(db.String(64))
    email = db.Column(db.String(64))
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    role = db.relationship('Role', back_populates='users')

    @staticmethod
    def create(role, id=None, username=None, name=None, email=None, member_since=None, password=None, **kwargs):
        filter_kwargs = {}
        for param in ['id', 'username', 'name', 'email', 'member_since', 'password']:
            if eval(param) is not None:
                filter_kwargs[param] = eval(param)
        filter_kwargs['role'] = role
        return User(**filter_kwargs)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Signal:
    _signals = {}

    def __init__(self, outer_class):
        self.outer_class = outer_class

    @classmethod
    def connect(cls, category, name):
        def decorator(func):
            func_name = func.__name__
            func_file = inspect.getsourcefile(func)

            if 'receivers' not in cls._signals[signal_name]:
                cls._signals[signal_name]['receivers'] = {}
            cls._signals[signal_name]['receivers'][func_file + '|' + func_name] = {
                'func': func,
                'func_name': func_name,
                'func_file': func_file
            }

        signal_name = category + '.' + name
        if signal_name not in cls._signals:
            cls._signals[signal_name] = {}
        return decorator

    def connect_this(self, name):
        return self.connect(self.outer_class.slug, name)

    @staticmethod
    def call_receiver_func(func, kwargs):
        parameters = inspect.signature(func).parameters
        if 'kwargs' in parameters:
            return func(**kwargs)
        pass_params = {key: kwargs[key] for key in parameters.keys()}
        return func(**pass_params)

    @classmethod
    def send(cls, _category, _name, **kwargs):
        from .settings import get_setting_value
        signal_name = _category + '.' + _name
        if signal_name not in cls._signals:
            return
        signal = cls._signals[signal_name]
        if 'return_type' in cls._signals[signal_name]:
            return_type = cls._signals[signal_name]['return_type']
            if return_type == 'single':
                if len(signal.get('receivers', {})) != 1:
                    return cls._signals[signal_name].get('default', None)
                return cls.call_receiver_func(next(iter(signal['receivers'].values()))['func'], kwargs)
            if return_type == 'list':
                if not signal.get('managed', False):
                    result = []
                    for receiver in signal['receivers'].values():
                        result.append(cls.call_receiver_func(receiver['func'], kwargs))
                    return result
                else:
                    result = []
                    signal_settings = get_setting_value(_name, category=_category)
                    if signal_settings is None or 'subscribers_order' not in signal_settings:
                        if signal['managed_default'] == 'all':
                            for receiver in signal.get('receivers', {}).values():
                                result.append(cls.call_receiver_func(receiver['func'], kwargs))
                            return result
                        elif signal['managed_default'] == 'none':
                            return []
                    else:
                        result = {}
                        for list_name, items in signal_settings['subscribers_order'].items():
                            result[list_name] = []
                            for item in items:
                                if item['is_on'] and item['subscriber'] in signal['receivers']:
                                    receiver = signal['receivers'][item['subscriber']]['func']
                                    result[list_name].append(cls.call_receiver_func(receiver, kwargs))
                        if 'main' in result and len(result) == 1:
                            result = result['main']
                        return result
            if return_type == 'merged_list':
                result = []
                for receiver in signal['receivers'].values():
                    item_result = cls.call_receiver_func(receiver['func'], kwargs)
                    if type(item_result) is list:
                        result.extend(item_result)
                    else:
                        result.append(item_result)
                return result
            if return_type == 'single_not_none':
                for receiver in signal['receivers'].values():
                    item_result = cls.call_receiver_func(receiver['func'], kwargs)
                    if item_result is not None:
                        return item_result
                raise ValueError()
        else:
            for receiver in signal['receivers'].values():
                cls.call_receiver_func(receiver['func'], kwargs)

    def send_this(self, name, **kwargs):
        return self.send(self.outer_class.slug, name, **kwargs)

    def declare_signal(self, name, **kwargs):
        signal_name = self.outer_class.slug + '.' + name
        if signal_name not in self._signals:
            self._signals[signal_name] = {}
        self._signals[signal_name].update(**kwargs)

    def get_signal(self, name):
        return self._signals[self.outer_class.slug + '.' + name]

    @property
    def signals(self):
        signals = {}
        for signal_name, data in self._signals.items():
            if signal_name.startswith(self.outer_class.slug + '.'):
                signals[signal_name[len(self.outer_class.slug + '.'):]] = data
        return signals


class Component:
    _components = {}
    _component_search_scope = [_components]

    @classmethod
    def find_component(cls, slug):
        for components in cls._component_search_scope:
            if slug in components:
                return components[slug]
        return None

    def __init__(self, name, directory, slug=None, show_in_sidebar=True, config=None):
        if slug is None:
            caller = inspect.getframeinfo(inspect.stack()[1][0])
            caller_path = caller.filename
            slug = Path(caller_path).parent.name
        self._components[slug] = self
        self.name = name
        self.slug = slug
        self.directory = directory
        self.show_in_sidebar = show_in_sidebar
        self.routes = {}
        self.signal = Signal(self)
        self.template_context = {}
        self.config = config or {}
        self.view_functions = {}
        self.rule_map = Map()
        self.view_route = self._instance_view_route
        self.view_url_for = self._instance_view_url_for

    def setup(self, app):
        if 'url_prefix' in self.config:
            if self.config['url_prefix'] is None:
                self.blueprint = Blueprint(self.name, self.slug)
            else:
                self.blueprint = Blueprint(self.name, self.slug, url_prefix=self.config['url_prefix'])
            self.urls = self.rule_map.bind('', '/')

            @self.blueprint.route('/', defaults={'path': ''})
            @self.blueprint.route('/<path:path>', methods=['GET', 'POST'])
            def route(path):
                endpoint, params = self.urls.match('/' + path, method=request.method)
                return self.view_functions[endpoint](**params)

    def done_setup(self, app):
        if 'url_prefix' in self.config:
            app.register_blueprint(self.blueprint)

    def route(self, blueprint, rule, name=None, **kwargs):
        def wrap(f):
            self.routes[rule] = Route(self, blueprint, rule, f, name)
            return f

        return wrap

    @classmethod
    def view_route(cls, rule, endpoint, component=None, **kwargs):
        if component is None:
            component = ComponentProxy._get_current_object()
        else:
            component = cls.find_component(component)
        return component._instance_view_route(rule, endpoint, **kwargs)

    def _instance_view_route(self, rule, endpoint, **kwargs):
        def wrap(f):
            self.rule_map.add(Rule(rule, endpoint=endpoint, methods=kwargs.get('methods', None) or ('GET',)))
            self.view_functions[endpoint] = f

        return wrap

    def request(self, path, **kwargs):
        rule = '/' + path.split('/')[0]
        if rule in self.routes:
            path = path[len(rule):]
            self.routes[rule].func(path=path, **kwargs)
        elif '/*' in self.routes:
            self.routes['/*'].func(path=path, **kwargs)

    def url_for(self, rule, **values):
        if len(values) == 0:
            return self.routes[rule].path()
        return self.routes[rule].path() + '?' + urlencode(values)

    @classmethod
    def view_url_for(cls, endpoint, component=None, **kwargs):
        if component is None:
            component = ComponentProxy._get_current_object()
        else:
            component = cls.find_component(component)

        return component._instance_view_url_for(endpoint, **kwargs)

    def _instance_view_url_for(self, endpoint, **kwargs):
        return (self.blueprint.url_prefix or '') + self.urls.build(endpoint, kwargs)

    def template_path(self, *args):
        return Path(self.slug, 'templates', *args).as_posix()

    @staticmethod
    def get_setting_value(key, component_name=None, default=None):
        from .settings import get_setting_value
        return get_setting_value(key, category=component_name, default=default)

    @staticmethod
    def get_setting(key, component_name=None):
        from .settings import get_setting
        return get_setting(key, category=component_name)

    def get_setting_value_this(self, key, default=None):
        return self.get_setting_value(key, self.slug, default=default)

    def get_setting_this(self, key):
        return self.get_setting(key, self.slug)

    def set_setting(self, key, **kwargs):
        from .settings import set_setting
        return set_setting(key, self.slug, **kwargs)

    def render_template(self, *args, **kwargs):
        return render_template(self.template_path(*args), **self.template_context, **kwargs)

    def context_func(self, f):
        self.template_context[f.__name__] = f
        return f


class ComponentProxy:
    root_path = Path(__file__).parent

    def __getattr__(self, item):
        return getattr(self._get_current_object(), item)

    def __eq__(self, other):
        return self._get_current_object() == other

    @classmethod
    def _get_current_object(cls):
        frame = sys._getframe()
        while frame is not None:
            path = os.path.abspath(frame.f_code.co_filename)
            if path.startswith(str(cls.root_path)):
                path = Path(path).relative_to(cls.root_path)
                component_slug = path.parts[0]
                if component_slug in Component._components:
                    return Component._components[component_slug]
            frame = frame.f_back


class Route:
    def __init__(self, plugin, blueprint, rule, func, name=None):
        self.plugin = plugin
        self.blueprint = blueprint
        self.rule = rule
        self.func = func
        self.name = name

    def path(self):
        return url_for(self.blueprint + '.route', path=self.plugin.slug + self.rule)
