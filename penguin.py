import os
from app import create_app, db
from app.models import PostType, Role, PostStatus
import click

app = create_app(os.getenv('FLASK_CONFIG') or 'default')


@app.cli.command()
def deploy():
    db.create_all()

    Role.insert_roles()
    PostType.insert_post_types()
    PostStatus.insert_post_statuses()


@app.cli.command()
@click.option('--application-name', default=None, help='specify the source application name. e.g. typecho')
@click.option('--db-url', default=None, help='url of the source database')
@click.option('--upload-parent-directory-path', default=None
    , help='parent directory path of the upload folder of the source application')
def migrate(application_name, db_url, upload_parent_directory_path):
    if application_name == 'typecho':
        from migrations.migrate import from_typecho
        from_typecho(db_url, upload_parent_directory_path)
