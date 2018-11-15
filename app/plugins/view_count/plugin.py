from . import signals
import json
from .models import ViewCount
from ...models import db


@signals.viewing.connect
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


@signals.get_count.connect
def get_count(sender, repository_id, count, **kwargs):
    view_count = ViewCount.query.filter_by(repository_id=repository_id).first()
    if view_count is not None:
        count['count'] = view_count.count


@signals.restore.connect
def restore(sender, repository_id, count, **kwargs):
    view_count = ViewCount.query.filter_by(repository_id=repository_id).first()
    if view_count is None:
        view_count = ViewCount(repository_id=repository_id, count=count)
        db.session.add(view_count)
        db.session.flush()
