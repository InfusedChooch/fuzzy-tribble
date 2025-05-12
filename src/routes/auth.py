from flask import Blueprint, render_template, request, redirect, url_for, session
import json
import os

auth_bp = Blueprint('auth', __name__)

# Load config file
def load_config():
    try:
        with open('data/config.json') as f:
            return json.load(f)
    except Exception:
        return {}

config = load_config()

@auth_bp.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == config.get('admin_username') and password == config.get('admin_password'):
            session['logged_in'] = True
            return redirect(url_for('admin.admin_view'))

        return render_template('admin_login.html', error='Incorrect login.')

    return render_template('admin_login.html')


@auth_bp.route('/admin_logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('auth.admin_login'))
