import json
from .models import ViewCount
from ...models import db
from ..models import Plugin

current_plugin = Plugin.current_plugin()


@current_plugin.signal.connect_this('viewing')
def viewing(sender, repository_id, request, cookies_to_set, **kwargs):
    view_count_repository_ids = request.cookies.get('view_count_repository_ids')
    if view_count_repository_ids is None:
        view_count_repository_ids = []
    else:
        view_count_repository_ids = json.loads(view_count_repository_ids)
    if repository_id not in view_count_repository_ids:
        view_count = ViewCount.query.filter_by(repository_id=repository_id).first()
        if view_count is None:
            view_count = ViewCount(repository_id=repository_id, count=0)
            db.session.add(view_count)
            db.session.flush()
        view_count.count += 1
        db.session.commit()
        view_count_repository_ids.append(repository_id)
        cookies_to_set['view_count_repository_ids'] = json.dumps(view_count_repository_ids)


@current_plugin.signal.connect_this('get_count')
def get_count(sender, repository_id, count, **kwargs):
    view_count = ViewCount.query.filter_by(repository_id=repository_id).first()
    if view_count is not None:
        count['count'] = view_count.count


@current_plugin.signal.connect_this('restore')
def restore(sender, repository_id, count, **kwargs):
    view_count = ViewCount.query.filter_by(repository_id=repository_id).first()
    if view_count is None:
        view_count = ViewCount(repository_id=repository_id, count=count)
        db.session.add(view_count)
        db.session.flush()


@current_plugin.signal.connect_this('get_rendered_view_count')
def get_rendered_view_count(sender, view_count, **kwargs):
    return current_plugin.render_template('view_count.html', view_count=view_count)
