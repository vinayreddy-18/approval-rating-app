from flask import Flask

from .admin.routes import ADMIN_EMAIL
from .database import init_db, seed_politicians


def create_app():
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )

    init_db()
    seed_politicians()

    @app.context_processor
    def inject_admin_context():
        return {'ADMIN_EMAIL': ADMIN_EMAIL}

    from .admin.routes import admin_bp
    from .auth.routes import auth_bp
    from .approval.routes import approval_bp
    from .pulse.routes import pulse_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(approval_bp)
    app.register_blueprint(pulse_bp)

    return app
