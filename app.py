import os
import tempfile
from flask import Flask
from models import db


def create_app(test_config=None):
    app = Flask(__name__)

    base_dir = os.path.abspath(os.path.dirname(__file__))

    # Use /tmp for uploads on cloud (ephemeral), local folder otherwise
    if os.environ.get('RENDER'):
        upload_folder = os.path.join(tempfile.gettempdir(), 'uploads')
    else:
        upload_folder = os.path.join(base_dir, 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    # Use DATABASE_URL from environment (Render PostgreSQL) or fallback to SQLite
    database_url = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(base_dir, "expense_tracker.db")}')
    # Render provides postgres:// but SQLAlchemy needs postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=upload_folder,
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,
        ALLOWED_EXTENSIONS={'xlsx', 'xls', 'csv'},
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    from routes import bp
    app.register_blueprint(bp)

    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
