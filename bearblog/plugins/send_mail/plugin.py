import os.path
import smtplib
import sys
import tempfile
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr

from flask import jsonify, request

from bearblog.plugins import current_plugin, Plugin, plugin_url_for, plugin_route
from bearblog.models import Signal


@Signal.connect('bearblog', 'deploy')
def deploy():
    current_plugin.set_setting('email', name='邮箱', value='', value_type='str')
    current_plugin.set_setting('password', name='密码', value='', value_type='str')
    current_plugin.set_setting('smtp_address', name='SMTP服务器', value='', value_type='str')


@Signal.connect('plugins', 'admin_sidebar_item')
def admin_sidebar_item():
    return {
        'name': current_plugin.name,
        'slug': current_plugin.slug,
        'items': [
            {
                'type': 'link',
                'name': '设置账号',
                'url': plugin_url_for('account', _component='admin')
            },
            {
                'type': 'link',
                'name': '测试发送邮件',
                'url': plugin_url_for('test-send-mail', _component='admin')
            }
        ]
    }


@plugin_route('/account', 'account', _component='admin')
def account():
    return Signal.send('settings', 'get_rendered_settings', category=current_plugin.slug, meta={'plugin': current_plugin.slug})


@plugin_route('/test-send-mail', 'test-send-mail', _component='admin')
def test_send_mail():
    if request.method == 'GET':
        return current_plugin.render_template('test_send_mail.html')
    elif request.method == 'POST':
        recipient = request.form.get('recipient')
        subject = request.form.get('subject')
        body = request.form.get('body')
        result = current_plugin.signal.send_this('send_mail', recipient=recipient, subject=subject, body=body)

        return jsonify(result)


@current_plugin.signal.connect_this('send_mail')
def send_mail(recipient, subject, body):
    is_success, error_log = send_email(recipient, subject, body)
    return {
        'status': is_success,
        'log': error_log
    }


def _format_address(s):
    name, address = parseaddr(s)
    return formataddr((Header(name, 'utf-8').encode(), address))


def send_email(to_address, subject, content):
    from_address = current_plugin.get_setting_value_this('email')
    password = current_plugin.get_setting_value_this('password')
    smtp_address = current_plugin.get_setting_value_this('smtp_address')

    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = _format_address(Plugin.get_setting_value('site_name') + from_address)
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
