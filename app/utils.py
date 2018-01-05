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
