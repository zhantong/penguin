from blinker import signal
import os
import smtplib
import tempfile
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr
import sys
from flask import current_app

sidebar = signal('sidebar')
edit = signal('edit')
submit = signal('submit')


def _format_address(s):
    name, address = parseaddr(s)
    return formataddr((Header(name, 'utf-8').encode(), address))


@sidebar.connect
def sidebar(sender, sidebars):
    sidebars.append(os.path.join('comment_to_mail', 'templates', 'sidebar.html'))


@edit.connect_via('comment_to_mail')
def edit(sender, contents, **kwargs):
    contents.append(os.path.join('comment_to_mail', 'templates', 'content.html'))


@submit.connect_via('comment_to_mail')
def submit(sender, args, form, **kwargs):
    app = current_app._get_current_object()
    address = form['address']
    subject = form['subject']
    content = form['content']

    from_address = app.config['MAIL_USERNAME']
    password = app.config['MAIL_PASSWORD']

    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = _format_address('Penguin <%s>' % from_address)
    msg['To'] = _format_address('%s <%s>' % (address, address))
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
        smtp.sendmail(from_address, [address], msg.as_string())
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
    print(stderr_bytes.decode())
    return is_success
