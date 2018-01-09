import os
from app import create_app, db
from app.models import PostType, Role
import click

app = create_app(os.getenv('FLASK_CONFIG') or 'default')


@app.cli.command()
def deploy():
    db.create_all()

    Role.insert_roles()
    PostType.insert_post_types()


@app.cli.command()
@click.option('--application-name', default=None, help='specify the source application name. e.g. typecho')
@click.option('--db-url', default=None, help='url of the source database')
def migrate(application_name, db_url):
    if application_name == 'typecho':
        from migrations.migrate import from_typecho
        from_typecho(db_url)
