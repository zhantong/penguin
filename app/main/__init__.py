from flask import Blueprint

main = Blueprint('main', __name__)

from . import views
from flask_bootstrap.nav import BootstrapRenderer
from flask_nav.elements import Navbar, View
from ..models import Post, PostType


class NavbarRenderer(BootstrapRenderer):
    def visit_Navbar(self, node):
        nav_tag = super(NavbarRenderer, self).visit_Navbar(node)
        nav_tag['class'] = 'navbar navbar-default navbar-fixed-top'
        return nav_tag


def navbar():
    pages = Post.query.filter_by(post_type=PostType.page()).all()
    items = [View('首页', 'main.show_articles')]
    items.extend(View(page.title, 'main.show_page', slug=page.slug) for page in pages)
    return Navbar('Penguin', *items)
