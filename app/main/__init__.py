from flask import Blueprint
from blinker import signal

navbar = signal('navbar')

main = Blueprint('main', __name__)

from . import views
from flask_bootstrap.nav import BootstrapRenderer
from flask_nav.elements import Navbar


class NavbarRenderer(BootstrapRenderer):
    def visit_Navbar(self, node):
        nav_tag = super(NavbarRenderer, self).visit_Navbar(node)
        nav_tag['class'] = 'navbar navbar-default navbar-fixed-top'
        return nav_tag


def custom_navbar():
    items = []
    navbar.send(items=items)
    return Navbar('Penguin', *items)
