import json
import os
from datetime import datetime

from app import db
from app.models import Role, User
from app.models import Signal


class Restore:
    def __init__(self, file_path):
        self.file_path = file_path
        with open(file_path, 'r') as f:
            self.data = json.loads(f.read())

    def process_admin(self, admins):
        for admin in admins:
            a = User.create(role=Role.admin(), username=admin['username'], name=admin['name'], email=admin['email'], member_since=datetime.utcfromtimestamp(admin['member_since']), password='123456')
            db.session.add(a)
        db.session.flush()

    def restore(self):
        self.process_admin(self.data['admin'])
        Signal.send('app', 'restore', data=self.data, directory=os.path.dirname(self.file_path))
        db.session.commit()
