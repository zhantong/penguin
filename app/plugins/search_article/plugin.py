import os.path
from ...signals import navbar
from ..article_list.signals import custom_article_list


@navbar.connect
def navbar(sender, content, **kwargs):
    content['others'].append(os.path.join('search_article', 'templates', 'main', 'navbar.html'))


@custom_article_list.connect
def custom_article_list(sender, args, query):
    if 'search' in args and args['search'] != '':
        search = args['search']
        query['query'] = query['query'].whoosh_search(search)
