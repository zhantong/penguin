import hashlib
from slugify import Slugify


def format_comments(comments):
    def process_children(parents, parent):
        result = []
        if parent in parents:
            for c in parents[parent]:
                result.append({
                    'comment': c,
                    'children': process_children(parents, c.id)
                })
        return result

    parents = {}
    for comment in comments:
        if comment.parent not in parents:
            parents[comment.parent] = []
        parents[comment.parent].append(comment)
    return process_children(parents, 0)


def md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def slugify(string):
    slugify = Slugify(translate=None)
    return slugify(string)
