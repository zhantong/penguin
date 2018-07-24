from ...signals import navbar
from ..article_list.signals import custom_article_list
from ...plugins import add_template_file
from pathlib import Path


@navbar.connect
def navbar(sender, content, **kwargs):
    add_template_file(content['others'], Path(__file__), 'templates', 'main', 'navbar.html')


@custom_article_list.connect
def custom_article_list(sender, args, query):
    if 'search' in args and args['search'] != '':
        search = args['search']
        query['query'] = query['query'].whoosh_search(search)
