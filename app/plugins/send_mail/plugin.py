from ..models import Plugin
from .models import Meta
from flask import render_template, jsonify
import os.path
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr
from email.header import Header
import tempfile
import smtplib
import sys
from . import signals
from ..settings.plugin import get_setting

send_mail = Plugin('发送邮件', 'send_mail')
send_mail_instance = send_mail


@send_mail.route('admin', '/account', '设置账号')
def account(request, templates, **kwargs):
    if request.method == 'GET':
        email = Meta.get('email')
        password = Meta.get('password')
        smtp_address = Meta.get('smtp_address')
        templates.append(
            render_template(send_mail_instance.template_path('account.html'), email=email, password=password,
                            smtp_address=smtp_address))
    elif request.method == 'POST':
        email = request.form.get('email', type=str)
        password = request.form.get('password', type=str)
        smtp_address = request.form.get('smtp-address', type=str)
        Meta.set('email', email)
        Meta.set('password', password)
        Meta.set('smtp_address', smtp_address)


@send_mail.route('admin', '/test-send-mail', '测试发送邮件')
def test_send_mail(request, meta, templates, scripts, **kwargs):
    if request.method == 'GET':
        templates.append(render_template(send_mail_instance.template_path('test_send_mail.html')))
        scripts.append(render_template(send_mail_instance.template_path('test_send_mail.js.html')))
    elif request.method == 'POST':
        recipient = request.form.get('recipient')
        subject = request.form.get('subject')
        body = request.form.get('body')
        result = {}
        signals.send_mail.send(recipient=recipient, subject=subject, body=body, result=result)

        meta['override_render'] = True
        templates.append(jsonify(result))


@signals.send_mail.connect
def send_mail(sender, recipient, subject, body, result, **kwargs):
    is_success, error_log = send_email(recipient, subject, body)
    result['status'] = is_success
    result['log'] = error_log


def _format_address(s):
    name, address = parseaddr(s)
    return formataddr((Header(name, 'utf-8').encode(), address))


def send_email(to_address, subject, content):
    from_address = Meta.get('email')
    password = Meta.get('password')
    smtp_address = Meta.get('smtp_address')

    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = _format_address(get_setting('site_name') + from_address)
    msg['To'] = _format_address('%s <%s>' % (to_address, to_address))
    msg['Subject'] = Header(subject, 'utf-8').encode()

    log_file = tempfile.TemporaryFile()
    available_fd = log_file.fileno()
    log_file.close()
    os.dup2(2, available_fd)
    log_file = tempfile.TemporaryFile()
    os.dup2(log_file.fileno(), 2)

    try:
        smtp = smtplib.SMTP_SSL(smtp_address, 465)
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
