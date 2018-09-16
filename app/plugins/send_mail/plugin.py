from ..models import Plugin
from .models import Meta
from flask import render_template
import os.path

send_mail = Plugin('发送邮件', 'send_mail')
send_mail_instance = send_mail


@send_mail.route('admin', '/account', '设置账号')
def account(request, templates, **kwargs):
    if request.method == 'GET':
        email = Meta.get('email')
        password = Meta.get('password')
        smtp_address = Meta.get('smtp_address')
        templates.append(
            render_template(os.path.join('send_mail', 'templates', 'account.html'), email=email, password=password,
                            smtp_address=smtp_address))
    elif request.method == 'POST':
        email = request.form.get('email', type=str)
        password = request.form.get('password', type=str)
        smtp_address = request.form.get('smtp-address', type=str)
        Meta.set('email', email)
        Meta.set('password', password)
        Meta.set('smtp_address', smtp_address)
