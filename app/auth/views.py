from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user
from . import auth
from .forms import LoginForm
from ..models import User


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is not None:
            password = form.password.data
            if user.verify_password(password):
                login_user(user, form.remember_me.data)
                next = request.args.get('next')
                if next is None or not next.startswith('/'):
                    next = url_for('admin.index')
                return redirect(next)
        flash('用户名或密码错误')
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已注销')
    return redirect(url_for('main.index'))
