import random

import factory
from faker import Faker

from app.models import Client, Parking

fake = Faker()


class ClientFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Client
        sqlalchemy_session_persistence = "commit"

    name = factory.Faker("first_name")
    surname = factory.Faker("last_name")
    credit_card = factory.LazyFunction(
        lambda: random.choice([None, fake.credit_card_number()])
    )
    car_number = factory.Faker("bothify", text="??###??")


class ParkingFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Parking
        sqlalchemy_session_persistence = "commit"

    address = factory.Faker("address")
    opened = factory.Faker("pybool")
    count_places = factory.Faker("random_int", min=1, max=100)
    count_available_places = factory.LazyAttribute(lambda obj: obj.count_places)
