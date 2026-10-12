"""Password login locks after repeated failures; unlock restores access."""

from collections.abc import Generator

import pytest
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users.password import PasswordHelper
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import onyx.auth.login_lockout as lockout_module
import onyx.auth.users as users_module
from onyx.auth.login_lockout import (
    clear_failed_login_attempts,
    unlock_user_login,
)
from onyx.db.engine.async_sql_engine import get_async_session_context_manager
from onyx.db.models import User
from onyx.server.security.store import _build_env_defaults
from onyx.server.utils import BasicAuthenticationError
from tests.external_dependency_unit.conftest import create_test_user, delete_test_user

_PASSWORD = "Correct-Horse-Battery-9!"
_WRONG_PASSWORD = "Wrong-Password-Not-It-1!"
_MAX_ATTEMPTS = 3


@pytest.fixture
def locked_user_setup(
    db_session: Session,
    tenant_context: None,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[User, None, None]:
    monkeypatch.setattr(lockout_module, "LOGIN_LOCKOUT_MAX_ATTEMPTS", _MAX_ATTEMPTS)
    monkeypatch.setattr(lockout_module, "LOGIN_LOCKOUT_WINDOW_SECONDS", 900)
    settings = _build_env_defaults().model_copy(update={"password_auth_enabled": True})
    monkeypatch.setattr(users_module, "get_security_settings", lambda: settings)

    user = create_test_user(db_session, "login_lockout")
    user.hashed_password = PasswordHelper().hash(_PASSWORD)
    db_session.commit()
    clear_failed_login_attempts(user.email)
    yield user
    clear_failed_login_attempts(user.email)
    delete_test_user(db_session, user)
    db_session.commit()


def _manager(async_session: AsyncSession) -> users_module.UserManager:
    return users_module.UserManager(SQLAlchemyUserDatabase(async_session, User))


def _credentials(email: str, password: str) -> OAuth2PasswordRequestForm:
    return OAuth2PasswordRequestForm(username=email, password=password)


@pytest.mark.asyncio
async def test_failed_logins_lock_account_until_admin_unlocks(
    db_session: Session,
    locked_user_setup: User,
) -> None:
    user = locked_user_setup

    async with get_async_session_context_manager() as async_session:
        manager = _manager(async_session)
        for _ in range(_MAX_ATTEMPTS - 1):
            result = await manager.authenticate(
                _credentials(user.email, _WRONG_PASSWORD)
            )
            assert result is None

        with pytest.raises(BasicAuthenticationError) as lock_exc:
            await manager.authenticate(_credentials(user.email, _WRONG_PASSWORD))
        assert lock_exc.value.detail == "ACCOUNT_LOCKED"

    db_session.refresh(user)
    assert user.login_locked_at is not None

    async with get_async_session_context_manager() as async_session:
        with pytest.raises(BasicAuthenticationError) as still_locked:
            await _manager(async_session).authenticate(
                _credentials(user.email, _PASSWORD)
            )
        assert still_locked.value.detail == "ACCOUNT_LOCKED"

    unlock_user_login(user, db_session)
    db_session.refresh(user)
    assert user.login_locked_at is None

    async with get_async_session_context_manager() as async_session:
        authenticated = await _manager(async_session).authenticate(
            _credentials(user.email, _PASSWORD)
        )
    assert authenticated is not None
    assert authenticated.id == user.id


@pytest.mark.asyncio
async def test_successful_login_clears_failure_counter(
    db_session: Session,
    locked_user_setup: User,
) -> None:
    user = locked_user_setup

    async with get_async_session_context_manager() as async_session:
        manager = _manager(async_session)
        for _ in range(_MAX_ATTEMPTS - 1):
            assert (
                await manager.authenticate(_credentials(user.email, _WRONG_PASSWORD))
                is None
            )

        authenticated = await manager.authenticate(_credentials(user.email, _PASSWORD))
        assert authenticated is not None

        for _ in range(_MAX_ATTEMPTS - 1):
            assert (
                await manager.authenticate(_credentials(user.email, _WRONG_PASSWORD))
                is None
            )

    db_session.refresh(user)
    assert user.login_locked_at is None
