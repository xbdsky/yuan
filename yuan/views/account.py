# coding: utf-8

from flask import Blueprint
from flask import g, request, json
from flask import render_template, redirect, url_for, jsonify
from flask.ext.babel import gettext as _
from ..models import Account
from ..helpers import login_user, logout_user, create_auth_token
from ..forms import SignupForm, SigninForm

bp = Blueprint('account', __name__)


@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        user = form.save()
        login_user(user)
        next_url = request.args.get('next', url_for('.settings'))
        return redirect(next_url)
    return render_template('signup.html', form=form)


@bp.route('/signin', methods=['GET', 'POST'])
def signin():
    next_url = request.args.get('next', '/')
    if g.user:
        return redirect(next_url)
    form = SigninForm()
    if form.validate_on_submit():
        login_user(form.user)
        return redirect(next_url)
    return render_template('signin.html', form=form)


@bp.route('/signout')
def signout():
    next_url = request.args.get('next', '/')
    logout_user()
    return redirect(next_url)


@bp.route('/settings')
def settings():
    return render_template('settings.html')


@bp.route('/login', methods=['POST'])
def login():
    ctype = request.headers.get('CONTENT_TYPE')
    if ctype != 'application/json':
        response = jsonify(
            status='error', message=_('Only application/json is allowed.')
        )
        response.status_code = 403
        return response
    try:
        data = json.loads(request.data)
    except Exception as e:
        response = jsonify(status='error', message=e)
        response.status_code = 500
        return response
    if 'account' in data and 'password' in data:
        account = data['account']
        if '@' in account:
            user = Account.query.filter_by(email=account).first()
        else:
            user = Account.query.filter_by(name=account).first()
        if user and user.check_password(data['password']):
            auth = create_auth_token(user)
            return jsonify(status='success', data={'auth': auth})
        response = jsonify(
            status='error',
            message=_('Wrong account or password')
        )
        response.status_code = 403
        return response
    response = jsonify(
        status='error',
        message=_('Parameters missing.')
    )
    response.status_code = 403
    return response