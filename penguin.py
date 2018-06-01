import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

from app import create_app, db
from app.plugins.post.models import PostStatus
from app.models import Role
import click
import json
from io import BytesIO
from zipfile import ZipFile
from urllib.request import urlopen

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


@app.cli.command()
def download_js_packages():
    def download_js_package(config_file_path):
        with open(config_file_path, 'r') as f:
            config = json.loads(f.read())
        for name, url in config.items():
            print(name, url)
            with urlopen(url) as resp:
                with ZipFile(BytesIO(resp.read())) as zipfile:
                    zipfile.extractall(os.path.dirname(config_file_path))

    download_js_package(os.path.abspath('app/static/package.json'))

    for name in os.listdir('app/plugins/'):
        config_file_path = os.path.abspath(os.path.join('app/plugins', name, 'static', 'package.json'))
        if os.path.exists(config_file_path):
            download_js_package(config_file_path)
