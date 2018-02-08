from . import signals
from ...models import db, PostStatus, PostVersion
import os.path


@signals.edit_article.connect
def edit_article(sender, widgets, **kwargs):
    widgets.append(os.path.join('post_version', 'templates', 'admin', 'widget_content.html'))


@signals.submit_article.connect
def submit_article(sender, form, post, **kwargs):
    if post.post_status == PostStatus.published():
        version = form['post-version-version']
        remark = form['post-version-remark']
        post_version = PostVersion(post=post, body=post.body, body_html=post.body_html, version=version, remark=remark)
        db.session.add(post_version)
        db.session.commit()


@signals.article.connect
def article(sender, args, post, context, article_content, before_contents, **kwargs):
    context['post_versions'] = post.post_versions
    before_contents.append(os.path.join('post_version', 'templates', 'main', 'content.html'))
    if 'post_version' in args:
        context['versioned_post'] = PostVersion.query.get(args.get('post_version', int))
        article_content['article_content'] = os.path.join('post_version', 'templates', 'main', 'article_content.html')
