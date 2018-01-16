import hashlib
from slugify import Slugify


def format_comments(comments, parent=0):
    result = []
    for comment in comments:
        if comment.parent == parent:
            comments.remove(comment)
            result.append({
                'comment': comment,
                'children': format_comments(comments, comment.id)
            })
    return result


def md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def slugify(string):
    slugify = Slugify(translate=None)
    return slugify(string)
