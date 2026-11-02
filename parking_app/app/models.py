from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

db = SQLAlchemy()


class Client(db.Model):  # type: ignore[name-defined]
    __tablename__ = "client"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(50), nullable=False)
    surname: Mapped[str] = mapped_column(db.String(50), nullable=False)
    credit_card: Mapped[str | None] = mapped_column(db.String(50))
    car_number: Mapped[str | None] = mapped_column(db.String(10))

    parking_logs: Mapped[list["ClientParking"]] = relationship(back_populates="client")


class Parking(db.Model):  # type: ignore[name-defined]
    __tablename__ = "parking"

    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(db.String(100), nullable=False)
    opened: Mapped[bool | None] = mapped_column(db.Boolean)
    count_places: Mapped[int] = mapped_column(nullable=False)
    count_available_places: Mapped[int] = mapped_column(nullable=False)

    parking_logs: Mapped[list["ClientParking"]] = relationship(back_populates="parking")


class ClientParking(db.Model):  # type: ignore[name-defined]
    __tablename__ = "client_parking"
    __table_args__ = (
        UniqueConstraint("client_id", "parking_id", name="unique_client_parking"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("client.id"))
    parking_id: Mapped[int | None] = mapped_column(ForeignKey("parking.id"))
    time_in: Mapped[datetime | None] = mapped_column(db.DateTime)
    time_out: Mapped[datetime | None] = mapped_column(db.DateTime)

    client: Mapped[Client | None] = relationship(back_populates="parking_logs")
    parking: Mapped[Parking | None] = relationship(back_populates="parking_logs")
