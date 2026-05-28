import pytest
from django.contrib.auth.models import User


@pytest.fixture
def user(db: None) -> User:
    return User.objects.create_user(username="tester", password="pass1234")
