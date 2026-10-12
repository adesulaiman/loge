"""Per-email password login failure tracking and durable account lockout.

Attempt counts live in CacheBackend (TTL = the failure window). The durable
lock is ``User.login_locked_at`` and is cleared only by an admin unlock.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from onyx.cache.factory import get_cache_backend
from onyx.configs.app_configs import (
    LOGIN_LOCKOUT_MAX_ATTEMPTS,
    LOGIN_LOCKOUT_WINDOW_SECONDS,
)
from onyx.db.models import User

_ATTEMPT_KEY_PREFIX = "login_fail:"


def _attempt_key(email: str) -> str:
    return f"{_ATTEMPT_KEY_PREFIX}{email.strip().lower()}"


def clear_failed_login_attempts(email: str) -> None:
    get_cache_backend().delete(_attempt_key(email))


def record_failed_login_attempt(email: str) -> int:
    """Bump the failure counter for ``email``. Returns the new count."""
    if LOGIN_LOCKOUT_MAX_ATTEMPTS <= 0 or LOGIN_LOCKOUT_WINDOW_SECONDS <= 0:
        return 0

    cache = get_cache_backend()
    key = _attempt_key(email)
    raw = cache.get(key)
    count = int(raw.decode("utf-8") if raw else "0") + 1
    cache.set(key, count, ex=LOGIN_LOCKOUT_WINDOW_SECONDS)
    return count


def should_lock_after_failures(failure_count: int) -> bool:
    if LOGIN_LOCKOUT_MAX_ATTEMPTS <= 0:
        return False
    return failure_count >= LOGIN_LOCKOUT_MAX_ATTEMPTS


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def unlock_user_login(user: User, db_session: Session) -> None:
    user.login_locked_at = None
    db_session.add(user)
    db_session.commit()
    clear_failed_login_attempts(user.email)


def is_user_login_locked(user: User) -> bool:
    return user.login_locked_at is not None
