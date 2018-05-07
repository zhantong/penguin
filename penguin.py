import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

from app import create_app, db
from app.plugins.post.models import PostStatus
from app.models import Role
import click

app = create_app(os.environ.get('FLASK_CONFIG', 'default'))


@app.cli.command()
def deploy():
    db.create_all()

    Role.insert_roles()
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
