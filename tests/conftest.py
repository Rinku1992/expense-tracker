import os
import tempfile
import pytest
from app import create_app
from models import db as _db


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'UPLOAD_FOLDER': tempfile.mkdtemp(),
    }

    app = create_app(test_config)

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield _db
