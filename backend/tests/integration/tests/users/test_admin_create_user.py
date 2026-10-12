"""Integration tests for admin password-based user provisioning.

Verifies:
- An admin can create an active user with email + password
- The created user can log in with that password
- A non-admin cannot call the endpoint
- Creating a duplicate email fails
"""

from uuid import uuid4

from onyx.server.models import FullUserSnapshot
from tests.integration.common_utils.constants import API_SERVER_URL
from tests.integration.common_utils.http_client import client
from tests.integration.common_utils.managers.user import DEFAULT_PASSWORD, UserManager
from tests.integration.common_utils.test_models import DATestUser


def _create_user_as(
    actor: DATestUser,
    email: str,
    password: str = DEFAULT_PASSWORD,
    is_admin: bool = False,
) -> tuple[int, dict]:
    response = client.post(
        url=f"{API_SERVER_URL}/manage/admin/create-user",
        json={"email": email, "password": password, "is_admin": is_admin},
        headers=actor.headers,
    )
    body: dict = {}
    try:
        body = response.json()
    except Exception:
        pass
    return response.status_code, body


def test_admin_create_user_can_login(admin_user: DATestUser) -> None:
    email = f"provisioned_{uuid4().hex[:8]}@example.com"

    status, body = _create_user_as(admin_user, email)
    assert status == 200, body
    snapshot = FullUserSnapshot(**body)
    assert snapshot.email == email
    assert snapshot.is_active is True
    assert snapshot.is_admin is False

    provisioned = DATestUser(
        id=str(snapshot.id),
        email=email,
        password=DEFAULT_PASSWORD,
        headers=admin_user.headers.copy(),
        is_admin=False,
        is_active=True,
    )
    logged_in = UserManager.login_as_user(provisioned)
    assert logged_in.email == email


def test_non_admin_cannot_create_user(basic_user: DATestUser) -> None:
    email = f"denied_{uuid4().hex[:8]}@example.com"
    status, _body = _create_user_as(basic_user, email)
    assert status == 403


def test_admin_create_user_duplicate_email(admin_user: DATestUser) -> None:
    email = f"dup_{uuid4().hex[:8]}@example.com"

    status, body = _create_user_as(admin_user, email)
    assert status == 200, body

    status_dup, body_dup = _create_user_as(admin_user, email)
    assert status_dup == 409, body_dup
