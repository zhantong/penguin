from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, Content, Comment, Meta, Relationship
import json
import phpserialize
import uuid


class Dump:
    def __init__(self, db_url):
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        self.session = Session()
        self.data = {}

    @staticmethod
    def process_comments(comments, parent=0):
        result = []
        for comment in comments:
            if comment.parent == parent:
                comments.remove(comment)
                co = {
                    'body': comment.text,
                    'timestamp': comment.created,
                    'ip': comment.ip,
                    'agent': comment.agent
                }
                if comment.authorId != 0:
                    co['author'] = comment.author
                else:
                    co['author'] = {
                        'name': comment.author,
                        'email': comment.mail,
                        'member_since': comment.created
                    }
                co['children'] = Dump.process_comments(comments, comment.coid)
                result.append(co)
        return result

    @staticmethod
    def process_attachements(attachments):
        result = []
        for attachment in attachments:
            meta = {}
            for key, value in phpserialize.loads(bytes(attachment.text, 'utf-8')).items():
                if type(key) is bytes:
                    key = key.decode('utf-8')
                if type(value) is bytes:
                    value = value.decode('utf-8')
                meta[key] = value
            result.append({
                'original_filename': attachment.title,
                'file_path': meta['path'],
                'mime': meta['mime'],
                'timestamp': attachment.created
            })
        return result

    @staticmethod
    def process_categories(categories):
        return [category.name for category in categories]

    @staticmethod
    def process_tags(tags):
        return [tag.name for tag in tags]

    def dump_admin(self):
        self.data['admin'] = []
        for administrator in self.session.query(User).filter_by(group='administrator'):
            admin = {
                'username': administrator.name,
                'name': administrator.screenName,
                'email': administrator.mail,
                'member_since': administrator.created
            }
            self.data['admin'].append(admin)

    def dump_category(self):
        self.data['category'] = []
        for category in self.session.query(Meta).filter_by(type='category'):
            c = {
                'name': category.name,
                'description': category.description
            }
            self.data['category'].append(c)

    def dump_tag(self):
        self.data['tag'] = []
        for tag in self.session.query(Meta).filter_by(type='tag'):
            t = {
                'name': tag.name,
                'description': tag.description
            }
            self.data['tag'].append(t)

    def dump_article(self):
        self.data['article'] = []
        for post in self.session.query(Content).filter_by(type='post'):
            article = {
                'title': post.title,
                'slug': post.slug,
                'body': post.text.replace('<!--markdown-->', ''),
                'timestamp': post.created,
                'author': self.session.query(User).filter_by(uid=post.authorId).one().name
            }

            comments = self.session.query(Comment).filter_by(cid=post.cid).order_by(Comment.created).all()
            comments = Dump.process_comments(comments)
            article['comments'] = comments

            attachments = self.session.query(Content).filter_by(type='attachment', parent=post.cid).all()
            attachments = Dump.process_attachements(attachments)
            article['attachments'] = attachments

            categories = self.session.query(Meta).filter(Relationship.cid == post.cid).filter(
                Relationship.mid == Meta.mid).filter_by(type='category').all()
            categories = Dump.process_categories(categories)
            article['categories'] = categories

            tags = self.session.query(Meta).filter(Relationship.cid == post.cid).filter(
                Relationship.mid == Meta.mid).filter_by(type='tag').all()
            tags = Dump.process_tags(tags)
            article['tags'] = tags

            article['view_count'] = post.viewsNum

            article['version'] = {
                'repository_id': str(uuid.uuid4()),
                'status': 'published'
            }

            self.data['article'].append(article)

    def dump_page(self):
        self.data['page'] = []
        for page in self.session.query(Content).filter_by(type='page'):
            p = {
                'title': page.title,
                'slug': page.slug,
                'body': page.text.replace('<!--markdown-->', ''),
                'timestamp': page.created,
                'author': self.session.query(User).filter_by(uid=page.authorId).one().name
            }

            comments = self.session.query(Comment).filter_by(cid=page.cid).order_by(Comment.created).all()
            comments = Dump.process_comments(comments)
            p['comments'] = comments

            attachments = self.session.query(Content).filter_by(type='attachment', parent=page.cid).all()
            attachments = Dump.process_attachements(attachments)
            p['attachments'] = attachments

            p['view_count'] = page.viewsNum

            p['version'] = {
                'repository_id': str(uuid.uuid4()),
                'status': 'published'
            }

            self.data['page'].append(p)


if __name__ == '__main__':
    dump = Dump("mysql+pymysql://root:123456@localhost/typecho?charset=utf8mb4")
    dump.dump_admin()
    dump.dump_category()
    dump.dump_tag()
    dump.dump_article()
    dump.dump_page()
    with open('dump.json', 'w') as f:
        f.write(json.dumps(dump.data, ensure_ascii=False))
