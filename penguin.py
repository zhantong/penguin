import os
from app import create_app, db
from app.models import PostType, Role

app = create_app(os.getenv('FLASK_CONFIG') or 'default')


@app.cli.command()
def deploy():
    db.create_all()

    Role.insert_roles()
    PostType.insert_post_types()
