import pytest

from app.core.config import Settings
from app.core.security import SalesforceSession


@pytest.fixture
def settings():
    return Settings(
        sf_client_id="client-id",
        sf_client_secret="client-secret",
        session_secret="x" * 64,
        sf_api_version="v67.0",
        cookie_secure=False,
    )


@pytest.fixture
def sf_session():
    return SalesforceSession(
        access_token="access",
        refresh_token="refresh",
        instance_url="https://example.my.salesforce.com",
    )
