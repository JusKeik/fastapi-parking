from datetime import datetime

import pytest

from app.models import Client, Parking
from tests.factories import ClientFactory, ParkingFactory


@pytest.mark.parametrize(
    "url",
    [
        "/clients",
        "/clients/1",
    ],
)
def test_get_endpoints_return_200(client, url):
    response = client.get(url)

    assert response.status_code == 200
    assert response.is_json


def test_create_client(client, db):
    payload = {
        "name": "Petr",
        "surname": "Petrov",
        "credit_card": "4222222222222222",
        "car_number": "B456CD77",
    }

    response = client.post("/clients", json=payload)

    assert response.status_code == 201

    data = response.get_json()
    assert data["id"] is not None
    assert data["name"] == "Petr"
    assert data["surname"] == "Petrov"
    assert data["credit_card"] == "4222222222222222"
    assert data["car_number"] == "B456CD77"

    created_client = db.session.get(Client, data["id"])
    assert created_client is not None


def test_create_client_without_required_fields(client):
    response = client.post("/clients", json={})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_parking(client, db):
    payload = {
        "address": "ul. Pushkina 10",
        "opened": True,
        "count_places": 5,
        "count_available_places": 5,
    }

    response = client.post("/parkings", json=payload)

    assert response.status_code == 201

    data = response.get_json()
    assert data["id"] is not None
    assert data["address"] == "ul. Pushkina 10"
    assert data["opened"] is True
    assert data["count_places"] == 5
    assert data["count_available_places"] == 5

    created_parking = db.session.get(Parking, data["id"])
    assert created_parking is not None


def test_create_client_with_factory(client, db):
    clients_before = db.session.query(Client).count()

    client_obj = ClientFactory.build()

    payload = {
        "name": client_obj.name,
        "surname": client_obj.surname,
        "credit_card": client_obj.credit_card,
        "car_number": client_obj.car_number,
    }

    response = client.post("/clients", json=payload)

    assert response.status_code == 201

    data = response.get_json()
    assert data["id"] is not None
    assert data["name"] == client_obj.name
    assert data["surname"] == client_obj.surname
    assert data["credit_card"] == client_obj.credit_card
    assert data["car_number"] == client_obj.car_number

    clients_after = db.session.query(Client).count()
    assert clients_after == clients_before + 1


def test_create_parking_with_factory(client, db):
    parkings_before = db.session.query(Parking).count()

    parking = ParkingFactory.build()

    payload = {
        "address": parking.address,
        "opened": parking.opened,
        "count_places": parking.count_places,
        "count_available_places": parking.count_available_places,
    }

    response = client.post("/parkings", json=payload)

    assert response.status_code == 201

    data = response.get_json()
    assert data["id"] is not None
    assert data["address"] == parking.address
    assert data["opened"] == parking.opened
    assert data["count_places"] == parking.count_places
    assert data["count_available_places"] == parking.count_available_places

    parkings_after = db.session.query(Parking).count()
    assert parkings_after == parkings_before + 1


@pytest.mark.parking
def test_enter_parking(client, db):
    parking = db.session.get(Parking, 1)
    parking.opened = True
    parking.count_places = 10
    parking.count_available_places = 10
    db.session.commit()

    response = client.post(
        "/client_parkings",
        json={"client_id": 1, "parking_id": 1},
    )

    assert response.status_code == 201

    data = response.get_json()
    assert data["client_id"] == 1
    assert data["parking_id"] == 1
    assert data["time_in"] is not None
    assert data["time_out"] is None

    db.session.refresh(parking)
    assert parking.count_available_places == 9


@pytest.mark.parking
def test_enter_parking_with_factories(client, db):
    client_obj = ClientFactory(credit_card="4111111111111111")
    parking = ParkingFactory(
        opened=True,
        count_places=5,
        count_available_places=5,
    )

    response = client.post(
        "/client_parkings",
        json={
            "client_id": client_obj.id,
            "parking_id": parking.id,
        },
    )

    assert response.status_code == 201

    data = response.get_json()
    assert data["client_id"] == client_obj.id
    assert data["parking_id"] == parking.id
    assert data["time_in"] is not None
    assert data["time_out"] is None

    db.session.refresh(parking)
    assert parking.count_available_places == 4


@pytest.mark.parking
def test_repeated_enter_reuses_log(client, db):
    client_obj = ClientFactory(credit_card="4111111111111111")
    parking = ParkingFactory(
        opened=True,
        count_places=5,
        count_available_places=5,
    )

    first_response = client.post(
        "/client_parkings",
        json={
            "client_id": client_obj.id,
            "parking_id": parking.id,
        },
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/client_parkings",
        json={
            "client_id": client_obj.id,
            "parking_id": parking.id,
        },
    )

    assert second_response.status_code == 409
    assert second_response.get_json()["error"] == "Client is already on this parking"


@pytest.mark.parking
def test_enter_parking_without_places(client, db):
    parking = db.session.get(Parking, 1)
    parking.opened = True
    parking.count_places = 10
    parking.count_available_places = 0
    db.session.commit()

    response = client.post(
        "/client_parkings",
        json={"client_id": 1, "parking_id": 1},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "No available places"


@pytest.mark.parking
def test_enter_closed_parking(client, db):
    parking = db.session.get(Parking, 1)
    parking.opened = False
    parking.count_places = 10
    parking.count_available_places = 10
    db.session.commit()

    response = client.post(
        "/client_parkings",
        json={"client_id": 1, "parking_id": 1},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Parking is closed"


@pytest.mark.parking
def test_exit_parking(client, db):
    parking = db.session.get(Parking, 1)
    parking.opened = True
    parking.count_places = 10
    parking.count_available_places = 10
    db.session.commit()

    enter_response = client.post(
        "/client_parkings",
        json={"client_id": 1, "parking_id": 1},
    )
    assert enter_response.status_code == 201

    parking_before = db.session.get(Parking, 1)
    assert parking_before.count_available_places == 9

    exit_response = client.delete(
        "/client_parkings",
        json={"client_id": 1, "parking_id": 1},
    )

    assert exit_response.status_code == 200

    data = exit_response.get_json()
    assert data["time_in"] is not None
    assert data["time_out"] is not None

    time_in = datetime.fromisoformat(data["time_in"])
    time_out = datetime.fromisoformat(data["time_out"])
    assert time_out >= time_in

    payment = data["payment"]
    assert payment["card"] == "4111111111111111"
    assert payment["status"] == "paid"

    parking_after = db.session.get(Parking, 1)
    assert parking_after.count_available_places == 10


@pytest.mark.parking
def test_exit_parking_without_credit_card(client, db):
    parking = db.session.get(Parking, 1)
    parking.opened = True
    parking.count_places = 10
    parking.count_available_places = 10
    db.session.commit()

    client_obj = db.session.get(Client, 1)
    client_obj.credit_card = None
    db.session.commit()

    enter_response = client.post(
        "/client_parkings",
        json={"client_id": 1, "parking_id": 1},
    )
    assert enter_response.status_code == 201

    exit_response = client.delete(
        "/client_parkings",
        json={"client_id": 1, "parking_id": 1},
    )

    assert exit_response.status_code == 400
    assert exit_response.get_json()["error"] == "Client has no linked credit card"


@pytest.mark.parking
def test_exit_without_active_session(client):
    response = client.delete(
        "/client_parkings",
        json={"client_id": 1, "parking_id": 1},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "Active parking session not found"
