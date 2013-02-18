# coding: utf-8

import gevent
from flask import Flask
from flask import current_app, url_for, render_template
from flask.ext.babel import gettext as _
from flask_mail import Mail, Message
from .helpers import create_auth_token


def send_mail(config, msg):
    app = Flask('yuan')
    app.config = config
    with app.test_request_context():
        mail = Mail(app)
        mail.send(msg)


def signup_mail(user):
    config = current_app.config
    msg = Message(
        _("Signup for %(site)s", site=config['SITE_TITLE']),
        recipients=[user.email]
    )
    host = config.get('SITE_SECURE_URL', '') or config.get('SITE_URL', '')
    dct = {
        'host': host.rstrip('/'),
        'path': url_for('.signup'),
        'token': create_auth_token(user)
    }
    link = '%(host)s%(path)s?token=%(token)s' % dct
    html = render_template('email/signup.html', user=user, link=link)
    msg.html = html
    gevent.spawn(send_mail, config, msg)
