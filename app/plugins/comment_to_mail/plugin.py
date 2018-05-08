from blinker import signal
import os
import smtplib
import tempfile
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr
import sys
from flask import current_app
from ..comment.signals import comment_submitted
from .models import CommentToMail
from ...models import db
from threading import Thread

sidebar = signal('sidebar')
edit = signal('edit')
submit = signal('submit')


def _format_address(s):
    name, address = parseaddr(s)
    return formataddr((Header(name, 'utf-8').encode(), address))


def send_email(app, to_address, subject, content):
    from_address = app.config['MAIL_USERNAME']
    password = app.config['MAIL_PASSWORD']

    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = _format_address('Penguin <%s>' % from_address)
    msg['To'] = _format_address('%s <%s>' % (to_address, to_address))
    msg['Subject'] = Header(subject, 'utf-8').encode()

    log_file = tempfile.TemporaryFile()
    available_fd = log_file.fileno()
    log_file.close()
    os.dup2(2, available_fd)
    log_file = tempfile.TemporaryFile()
    os.dup2(log_file.fileno(), 2)

    try:
        smtp = smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        smtplib.stderr = log_file
        smtp.set_debuglevel(2)
        smtp.login(from_address, password)
        smtp.sendmail(from_address, [to_address], msg.as_string())
        smtp.quit()
    except smtplib.SMTPException as e:
        is_success = False
    else:
        is_success = True

    sys.stderr.flush()
    log_file.flush()
    log_file.seek(0)
    stderr_bytes = log_file.read()
    log_file.close()
    os.dup2(available_fd, 2)
    os.close(available_fd)

    return is_success, stderr_bytes.decode()


@sidebar.connect
def sidebar(sender, sidebars):
    sidebars.append(os.path.join('comment_to_mail', 'templates', 'sidebar.html'))


@edit.connect_via('comment_to_mail')
def edit(sender, contents, **kwargs):
    contents.append(os.path.join('comment_to_mail', 'templates', 'content.html'))


@submit.connect_via('comment_to_mail')
def submit(sender, args, form, **kwargs):
    app = current_app._get_current_object()
    is_sent, log = send_email(app, form['address'], form['subject'], form['content'])
    print(log)


@comment_submitted.connect
def comment_submitted(sender, comment, **kwargs):
    if comment.author.email:
        app = current_app._get_current_object()

        def async(app):
            with app.app_context():
                is_sent, log = send_email(app, comment.author.email, '新的评论', comment.body)
                comment_to_mail = CommentToMail(is_sent=is_sent, log=log, comment=comment)
                db.session.add(comment_to_mail)
                db.session.commit()

        thread = Thread(target=async, args=[app])
        thread.start()
