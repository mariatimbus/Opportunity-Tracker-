"""Application tracking tests: save, list, update, delete, ownership isolation."""

import itertools
import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select

from opportunity_api.models import Application, Opportunity, OpportunityType, User
from tests.conftest import auth_headers

URL = "/api/v1/applications"
_counter = itertools.count(1)


def make_opportunity(**overrides) -> Opportunity:
    n = next(_counter)
    fields = dict(
        title=f"Opportunity {n}",
        organization="Example Corp",
        opportunity_type=OpportunityType.internship,
        url=f"https://example.com/{n}",
        source="test",
        source_id=str(n),
        is_active=True,
    )
    fields.update(overrides)
    return Opportunity(**fields)


class UserFactory:
    """Mint one token per email per test and keep the persisted User row.

    A fresh ``auth_headers`` call mints a token with a new random ``sub``, so
    callers must reuse the same headers for a user within a test.
    """

    def __init__(self, client: TestClient, db_factory):
        self.client = client
        self.db_factory = db_factory
        self._cache: dict[str, tuple[dict[str, str], User]] = {}

    def get(self, email: str) -> tuple[dict[str, str], User]:
        if email not in self._cache:
            headers = auth_headers(self.client, email)
            self.client.get(URL, headers=headers)
            with self.db_factory() as session:
                user = session.scalar(select(User).where(User.email == email))
            self._cache[email] = (headers, user)
        return self._cache[email]


def seed(db_factory, *objects) -> None:
    with db_factory() as session:
        session.add_all(objects)
        session.commit()


def test_applications_require_auth(client: TestClient):
    assert client.get(URL).status_code == 401
    assert client.post(URL, json={}).status_code == 401
    assert client.patch(f"{URL}/{uuid.uuid4()}", json={}).status_code == 401
    assert client.delete(f"{URL}/{uuid.uuid4()}").status_code == 401


def test_create_saved_application(client: TestClient, db_factory):
    opportunity = make_opportunity()
    seed(db_factory, opportunity)
    headers, _ = UserFactory(client, db_factory).get("ada@example.com")

    response = client.post(URL, headers=headers, json={"opportunity_id": str(opportunity.id)})

    assert response.status_code == 201
    body = response.json()
    assert body["opportunity_id"] == str(opportunity.id)
    assert body["status"] == "saved"
    assert body["notes"] is None
    assert body["applied_at"] is None
    assert "user_id" not in body
    summary = body["opportunity"]
    assert summary["id"] == str(opportunity.id)
    assert summary["title"] == opportunity.title
    assert summary["organization"] == opportunity.organization


def test_create_application_for_missing_opportunity(client: TestClient, db_factory):
    headers, _ = UserFactory(client, db_factory).get("ada@example.com")

    response = client.post(URL, headers=headers, json={"opportunity_id": str(uuid.uuid4())})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "opportunity_not_found"


def test_duplicate_application_returns_409(client: TestClient, db_factory):
    opportunity = make_opportunity()
    seed(db_factory, opportunity)
    headers, _ = UserFactory(client, db_factory).get("ada@example.com")
    payload = {"opportunity_id": str(opportunity.id)}
    assert client.post(URL, headers=headers, json=payload).status_code == 201

    response = client.post(URL, headers=headers, json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "application_exists"


def test_list_only_current_user_applications(client: TestClient, db_factory):
    opportunity = make_opportunity()
    other_opportunity = make_opportunity()
    seed(db_factory, opportunity, other_opportunity)
    users = UserFactory(client, db_factory)
    _, user_a = users.get("a@example.com")
    _, user_b = users.get("b@example.com")
    headers_a, _ = users.get("a@example.com")
    seed(
        db_factory,
        Application(user_id=user_a.id, opportunity_id=opportunity.id),
        Application(user_id=user_b.id, opportunity_id=other_opportunity.id),
    )

    response = client.get(URL, headers=headers_a)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["opportunity"]["id"] == str(opportunity.id)


def test_filter_applications_by_status(client: TestClient, db_factory):
    opportunity_a = make_opportunity()
    opportunity_b = make_opportunity()
    seed(db_factory, opportunity_a, opportunity_b)
    users = UserFactory(client, db_factory)
    headers, user = users.get("ada@example.com")
    seed(
        db_factory,
        Application(user_id=user.id, opportunity_id=opportunity_a.id, status="saved"),
        Application(
            user_id=user.id,
            opportunity_id=opportunity_b.id,
            status="applied",
            applied_at=datetime.now(UTC),
        ),
    )

    response = client.get(URL, headers=headers, params={"status": "applied"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "applied"


def test_update_application_status(client: TestClient, db_factory):
    opportunity = make_opportunity()
    seed(db_factory, opportunity)
    users = UserFactory(client, db_factory)
    headers, user = users.get("ada@example.com")
    application = Application(user_id=user.id, opportunity_id=opportunity.id)
    seed(db_factory, application)

    response = client.patch(
        f"{URL}/{application.id}",
        headers=headers,
        json={"status": "interview"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "interview"
    assert body["applied_at"] is None


def test_update_application_notes(client: TestClient, db_factory):
    opportunity = make_opportunity()
    seed(db_factory, opportunity)
    users = UserFactory(client, db_factory)
    headers, user = users.get("ada@example.com")
    application = Application(user_id=user.id, opportunity_id=opportunity.id, notes="old")
    seed(db_factory, application)

    response = client.patch(
        f"{URL}/{application.id}",
        headers=headers,
        json={"notes": "new note"},
    )

    assert response.status_code == 200
    assert response.json()["notes"] == "new note"


def test_set_applied_at_when_applied(client: TestClient, db_factory):
    opportunity = make_opportunity()
    seed(db_factory, opportunity)
    users = UserFactory(client, db_factory)
    headers, user = users.get("ada@example.com")
    application = Application(user_id=user.id, opportunity_id=opportunity.id)
    seed(db_factory, application)

    response = client.patch(
        f"{URL}/{application.id}",
        headers=headers,
        json={"status": "applied"},
    )

    assert response.status_code == 200
    assert response.json()["applied_at"] is not None


def test_other_users_application_is_not_found(client: TestClient, db_factory):
    opportunity = make_opportunity()
    seed(db_factory, opportunity)
    users = UserFactory(client, db_factory)
    _, user_a = users.get("a@example.com")
    foreign_headers, _ = users.get("b@example.com")
    application = Application(user_id=user_a.id, opportunity_id=opportunity.id)
    seed(db_factory, application)

    response = client.patch(
        f"{URL}/{application.id}", headers=foreign_headers, json={"status": "applied"}
    )
    assert response.status_code == 404
    assert client.delete(f"{URL}/{application.id}", headers=foreign_headers).status_code == 404


def test_delete_application(client: TestClient, db_factory):
    opportunity = make_opportunity()
    seed(db_factory, opportunity)
    users = UserFactory(client, db_factory)
    headers, user = users.get("ada@example.com")
    application = Application(user_id=user.id, opportunity_id=opportunity.id)
    seed(db_factory, application)

    response = client.delete(f"{URL}/{application.id}", headers=headers)

    assert response.status_code == 204
    assert client.get(URL, headers=headers).json()["total"] == 0


def test_invalid_application_uuid_returns_422(client: TestClient, db_factory):
    headers, _ = UserFactory(client, db_factory).get("ada@example.com")

    assert client.patch(f"{URL}/not-a-uuid", headers=headers, json={}).status_code == 422
    assert client.delete(f"{URL}/not-a-uuid", headers=headers).status_code == 422


def test_invalid_status_returns_422(client: TestClient, db_factory):
    opportunity = make_opportunity()
    seed(db_factory, opportunity)
    users = UserFactory(client, db_factory)
    headers, user = users.get("ada@example.com")
    application = Application(user_id=user.id, opportunity_id=opportunity.id)
    seed(db_factory, application)

    response = client.patch(
        f"{URL}/{application.id}",
        headers=headers,
        json={"status": "wishlist"},
    )

    assert response.status_code == 422
