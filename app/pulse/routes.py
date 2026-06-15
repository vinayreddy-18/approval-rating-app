from flask import Blueprint, render_template, request

pulse_bp = Blueprint('pulse', __name__)


@pulse_bp.route('/pulse')
def pulse_page():
    user_email = request.args.get('email', '').strip()
    return render_template('pulse.html', user_email=user_email)
