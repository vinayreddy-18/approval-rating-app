from flask import Blueprint, render_template

# Authentication blueprint placeholder
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/')
def auth_index():
    return '<p>Authentication module placeholder.</p>'
