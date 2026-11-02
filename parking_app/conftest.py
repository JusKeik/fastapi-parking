import pytest

from app import create_app
from app.models import ClientParking
from app.models import db as _db
from tests.factories import ClientFactory, ParkingFactory


@pytest.fixture
def app():
    app = create_app(
        test_config={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        _db.create_all()

        ClientFactory._meta.sqlalchemy_session = _db.session
        ParkingFactory._meta.sqlalchemy_session = _db.session

        client = ClientFactory(credit_card="4111111111111111")
        parking = ParkingFactory(
            opened=True,
            count_places=10,
            count_available_places=10,
        )

        parking_log = ClientParking(
            client_id=client.id,
            parking_id=parking.id,
            time_in=_db.func.now(),
            time_out=_db.func.now(),
        )

        _db.session.add(parking_log)
        _db.session.commit()

        yield app

        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield _db
