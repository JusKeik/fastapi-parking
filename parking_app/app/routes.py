from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue
from sqlalchemy import select

from app.models import Client, ClientParking, Parking, db


def client_to_dict(client: Client) -> dict:
    return {
        "id": client.id,
        "name": client.name,
        "surname": client.surname,
        "credit_card": client.credit_card,
        "car_number": client.car_number,
    }


def parking_to_dict(parking: Parking) -> dict:
    return {
        "id": parking.id,
        "address": parking.address,
        "opened": parking.opened,
        "count_places": parking.count_places,
        "count_available_places": parking.count_available_places,
    }


def parking_log_to_dict(log: ClientParking) -> dict:
    return {
        "id": log.id,
        "client_id": log.client_id,
        "parking_id": log.parking_id,
        "time_in": log.time_in.isoformat() if log.time_in else None,
        "time_out": log.time_out.isoformat() if log.time_out else None,
    }


def register_routes(app: Flask) -> None:
    @app.get("/clients")
    def get_clients() -> ResponseReturnValue:
        clients = db.session.scalars(select(Client)).all()
        return jsonify([client_to_dict(client) for client in clients])

    @app.get("/clients/<int:client_id>")
    def get_client(client_id: int) -> ResponseReturnValue:
        client = db.session.get(Client, client_id)

        if client is None:
            return jsonify({"error": "Client not found"}), 404

        return jsonify(client_to_dict(client))

    @app.post("/clients")
    def create_client() -> ResponseReturnValue:
        data = request.get_json(silent=True) or {}

        if not data.get("name") or not data.get("surname"):
            return jsonify({"error": "name and surname are required"}), 400

        client = Client(
            name=data["name"],
            surname=data["surname"],
            credit_card=data.get("credit_card"),
            car_number=data.get("car_number"),
        )

        db.session.add(client)
        db.session.commit()

        return jsonify(client_to_dict(client)), 201

    @app.post("/parkings")
    def create_parking() -> ResponseReturnValue:
        data = request.get_json(silent=True) or {}

        if not data.get("address"):
            return jsonify({"error": "address is required"}), 400

        count_places = data.get("count_places")
        count_available_places = data.get(
            "count_available_places",
            count_places,
        )

        if not isinstance(count_places, int) or count_places < 0:
            return (
                jsonify({"error": "count_places must be a non-negative integer"}),
                400,
            )

        if not isinstance(count_available_places, int) or not (
            0 <= count_available_places <= count_places
        ):
            return (
                jsonify(
                    {
                        "error": (
                            "count_available_places must be between "
                            "0 and count_places"
                        )
                    }
                ),
                400,
            )

        parking = Parking(
            address=data["address"],
            opened=data.get("opened", False),
            count_places=count_places,
            count_available_places=count_available_places,
        )

        db.session.add(parking)
        db.session.commit()

        return jsonify(parking_to_dict(parking)), 201

    @app.post("/client_parkings")
    def enter_parking() -> ResponseReturnValue:
        data = request.get_json(silent=True) or {}
        client_id = data.get("client_id")
        parking_id = data.get("parking_id")

        if not client_id or not parking_id:
            return jsonify({"error": "client_id and parking_id are required"}), 400

        client = db.session.get(Client, client_id)
        parking = db.session.get(Parking, parking_id)

        if client is None:
            return jsonify({"error": "Client not found"}), 404

        if parking is None:
            return jsonify({"error": "Parking not found"}), 404

        if not parking.opened:
            return jsonify({"error": "Parking is closed"}), 400

        if parking.count_available_places <= 0:
            return jsonify({"error": "No available places"}), 400

        log = db.session.scalar(
            select(ClientParking).where(
                ClientParking.client_id == client_id,
                ClientParking.parking_id == parking_id,
            )
        )

        if log is not None and log.time_out is None:
            return jsonify({"error": "Client is already on this parking"}), 409

        if log is None:
            log = ClientParking(
                client_id=client.id,
                parking_id=parking.id,
            )
            db.session.add(log)

        log.time_in = datetime.now(timezone.utc).replace(tzinfo=None)
        log.time_out = None

        parking.count_available_places -= 1
        db.session.commit()

        return jsonify(parking_log_to_dict(log)), 201

    @app.delete("/client_parkings")
    def exit_parking() -> ResponseReturnValue:
        data = request.get_json(silent=True) or {}
        client_id = data.get("client_id")
        parking_id = data.get("parking_id")

        if not client_id or not parking_id:
            return jsonify({"error": "client_id and parking_id are required"}), 400

        client = db.session.get(Client, client_id)
        parking = db.session.get(Parking, parking_id)

        if client is None:
            return jsonify({"error": "Client not found"}), 404

        if parking is None:
            return jsonify({"error": "Parking not found"}), 404

        log = db.session.scalar(
            select(ClientParking).where(
                ClientParking.client_id == client_id,
                ClientParking.parking_id == parking_id,
                ClientParking.time_out.is_(None),
            )
        )

        if log is None:
            return jsonify({"error": "Active parking session not found"}), 404

        if not client.credit_card:
            return jsonify({"error": "Client has no linked credit card"}), 400

        time_in = log.time_in

        if time_in is None:
            return jsonify({"error": "Parking session has no entry time"}), 409

        time_out = datetime.now(timezone.utc).replace(tzinfo=None)

        if time_out < time_in:
            return (
                jsonify({"error": "Exit time cannot be earlier than entry time"}),
                409,
            )

        duration = time_out - time_in
        hours = duration.total_seconds() / 3600
        amount = round(hours * 100, 2)

        log.time_out = time_out
        parking.count_available_places += 1

        db.session.commit()

        return jsonify(
            {
                **parking_log_to_dict(log),
                "payment": {
                    "card": client.credit_card,
                    "amount": amount,
                    "currency": "RUB",
                    "status": "paid",
                },
            }
        )
