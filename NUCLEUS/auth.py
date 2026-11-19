"""auth.py — User management and role-based access control (RBAC) for NUCLEUS.

A lightweight, dependency-free governance layer. Users are persisted to a local
JSON store (``users.json`` next to this module) with salted password hashing via
``hashlib`` — no external packages required for this MVP.

Three roles bind directly to NUCLEUS feature permissions:

* ``administrator`` — full access (user management, monitoring, analytics,
  file upload, system settings).
* ``engineer``      — full analytics (upload, select metrics, run forecasts,
  view insight) plus monitoring. No user management.
* ``viewer``        — read-only view of analytics and monitoring. Cannot upload
  files or mutate anything.

The module never imports Streamlit so it stays unit-testable in isolation.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

# --------------------------------------------------------------------------- #
# Roles and permissions
# --------------------------------------------------------------------------- #
ROLE_ADMIN = "administrator"
ROLE_ENGINEER = "engineer"
ROLE_VIEWER = "viewer"
ROLES = (ROLE_ADMIN, ROLE_ENGINEER, ROLE_VIEWER)

# Canonical permission flags used throughout the app.
PERM_USER_MANAGEMENT = "user_management"   # view/manage the User Management page
PERM_SYSTEM_SETTINGS = "system_settings"   # change system-level settings
PERM_VIEW_ANALYTICS = "view_analytics"     # open the Analytics module
PERM_VIEW_MONITORING = "view_monitoring"   # open the Monitoring module
PERM_UPLOAD_FILE = "upload_file"           # upload data / use own data
PERM_RUN_FORECAST = "run_forecast"         # change settings & run forecasts
PERM_MANAGE_DATABASE = "manage_database"   # open the Database module

# role -> set of granted permissions.
_ROLE_PERMISSIONS: dict[str, set] = {
    ROLE_ADMIN: {
        PERM_USER_MANAGEMENT, PERM_SYSTEM_SETTINGS, PERM_VIEW_ANALYTICS,
        PERM_VIEW_MONITORING, PERM_UPLOAD_FILE, PERM_RUN_FORECAST,
        PERM_MANAGE_DATABASE,
    },
    ROLE_ENGINEER: {
        PERM_VIEW_ANALYTICS, PERM_VIEW_MONITORING,
        PERM_UPLOAD_FILE, PERM_RUN_FORECAST,
    },
    ROLE_VIEWER: {
        PERM_VIEW_ANALYTICS, PERM_VIEW_MONITORING,
    },
}


def role_permissions(role: str) -> set:
    """Return the permission set for ``role`` (empty set if unknown)."""
    return set(_ROLE_PERMISSIONS.get((role or "").lower(), set()))


def has_permission(role: str, permission: str) -> bool:
    """True if ``role`` grants ``permission``."""
    return permission in role_permissions(role)


# --------------------------------------------------------------------------- #
# Password hashing (salted SHA-256 — stdlib only)
# --------------------------------------------------------------------------- #
def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Return ``(salt, hash)`` for ``password``. Generates a salt if omitted."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return salt, digest


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Constant-time check that ``password`` matches the stored salt+hash."""
    _, digest = _hash_password(password, salt)
    return secrets.compare_digest(digest, expected_hash)


# --------------------------------------------------------------------------- #
# User record
# --------------------------------------------------------------------------- #
@dataclass
class User:
    username: str
    full_name: str
    email: str
    role: str
    active: bool = True
    salt: str = ""
    password_hash: str = ""

    def public_dict(self) -> dict:
        """Serializable view without the password material."""
        return {
            "username": self.username,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
            "active": self.active,
        }

    def _storage_dict(self) -> dict:
        d = self.public_dict()
        d["salt"] = self.salt
        d["password_hash"] = self.password_hash
        return d


# --------------------------------------------------------------------------- #
# Persistent store
# --------------------------------------------------------------------------- #
_DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "users.json")


class UserStore:
    """A tiny JSON-backed user store with CRUD and authentication."""

    def __init__(self, path: str = _DEFAULT_PATH):
        self.path = path
        self._users: dict[str, User] = {}
        self._load()

    # ---- persistence ----------------------------------------------------- #
    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                for rec in data.get("users", []):
                    u = User(
                        username=rec["username"],
                        full_name=rec.get("full_name", ""),
                        email=rec.get("email", ""),
                        role=rec.get("role", ROLE_VIEWER),
                        active=bool(rec.get("active", True)),
                        salt=rec.get("salt", ""),
                        password_hash=rec.get("password_hash", ""),
                    )
                    self._users[u.username] = u
            except (json.JSONDecodeError, KeyError, OSError):
                self._users = {}
        if not self._users:
            self._seed_defaults()
            self._save()

    def _save(self) -> None:
        payload = {"users": [u._storage_dict() for u in self._users.values()]}
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    def _seed_defaults(self) -> None:
        """Seed an initial admin plus one engineer and one viewer (demo)."""
        seeds = [
            ("admin", "Administrator", "admin@nucleus.local", ROLE_ADMIN,
             "nucleus"),
            ("engineer", "Capacity Analyst", "engineer@nucleus.local",
             ROLE_ENGINEER, "engineer"),
            ("viewer", "Executive Viewer", "viewer@nucleus.local",
             ROLE_VIEWER, "viewer"),
        ]
        for username, full_name, email, role, pw in seeds:
            salt, digest = _hash_password(pw)
            self._users[username] = User(
                username=username, full_name=full_name, email=email,
                role=role, active=True, salt=salt, password_hash=digest,
            )

    # ---- queries ---------------------------------------------------------- #
    def list_users(self) -> list[User]:
        return sorted(self._users.values(), key=lambda u: u.username.lower())

    def get(self, username: str) -> Optional[User]:
        return self._users.get(username)

    def count_active_admins(self) -> int:
        return sum(1 for u in self._users.values()
                   if u.role == ROLE_ADMIN and u.active)

    # ---- authentication --------------------------------------------------- #
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Return the User when credentials are valid AND the account is active."""
        u = self._users.get(username)
        if not u or not u.active:
            return None
        if verify_password(password, u.salt, u.password_hash):
            return u
        return None

    # ---- mutations -------------------------------------------------------- #
    def add_user(self, username: str, full_name: str, email: str, role: str,
                 password: str, active: bool = True) -> User:
        username = (username or "").strip()
        if not username:
            raise ValueError("username_required")
        if username in self._users:
            raise ValueError("username_exists")
        if role not in ROLES:
            raise ValueError("invalid_role")
        if not password:
            raise ValueError("password_required")
        salt, digest = _hash_password(password)
        u = User(username=username, full_name=full_name.strip(),
                 email=email.strip(), role=role, active=active,
                 salt=salt, password_hash=digest)
        self._users[username] = u
        self._save()
        return u

    def update_user(self, username: str, *, full_name: Optional[str] = None,
                    email: Optional[str] = None, role: Optional[str] = None,
                    active: Optional[bool] = None,
                    password: Optional[str] = None) -> User:
        u = self._users.get(username)
        if not u:
            raise ValueError("user_not_found")
        if role is not None and role not in ROLES:
            raise ValueError("invalid_role")

        # Guard: never strip the last active administrator of admin rights.
        demoting_admin = (u.role == ROLE_ADMIN and u.active and (
            (role is not None and role != ROLE_ADMIN) or active is False))
        if demoting_admin and self.count_active_admins() <= 1:
            raise ValueError("last_admin")

        if full_name is not None:
            u.full_name = full_name.strip()
        if email is not None:
            u.email = email.strip()
        if role is not None:
            u.role = role
        if active is not None:
            u.active = active
        if password:
            u.salt, u.password_hash = _hash_password(password)
        self._save()
        return u

    def set_active(self, username: str, active: bool) -> User:
        return self.update_user(username, active=active)

    def delete_user(self, username: str) -> None:
        u = self._users.get(username)
        if not u:
            raise ValueError("user_not_found")
        if u.role == ROLE_ADMIN and u.active and self.count_active_admins() <= 1:
            raise ValueError("last_admin")
        del self._users[username]
        self._save()


# --------------------------------------------------------------------------- #
# Session tokens (persistent login across browser tabs)
# --------------------------------------------------------------------------- #
# A token is an opaque random string placed in the URL (?token=...). The server
# maps it to a username so a freshly opened tab can resume the session without
# re-entering credentials. Tokens live in the process (via the app's cached
# UserStore); they are not written to disk, so a server restart ends all
# sessions — acceptable for this MVP.
class SessionTokens:
    """In-memory token registry for cross-tab session resume.

    A token expires after ``idle_ttl`` seconds without ``touch`` so a stale
    ``?token=`` URL cannot bypass the idle timeout.
    """

    VERSION = 2
    _EXPIRED_CAP = 256

    def __init__(self, idle_ttl: float = 1800.0, clock: Callable[[], float] = time.time):
        self._ttl = float(idle_ttl)
        self._clock = clock
        self._tokens: dict[str, tuple[str, float]] = {}
        self._expired: dict[str, None] = {}

    def _purge(self) -> None:
        now = self._clock()
        for tok, (_, seen) in list(self._tokens.items()):
            if now - seen > self._ttl:
                del self._tokens[tok]
                self._expired[tok] = None
        while len(self._expired) > self._EXPIRED_CAP:
            self._expired.pop(next(iter(self._expired)))

    def issue(self, username: str) -> str:
        self._purge()
        token = secrets.token_urlsafe(24)
        self._tokens[token] = (username, self._clock())
        return token

    def username_for(self, token: str) -> Optional[str]:
        if not token:
            return None
        self._purge()
        entry = self._tokens.get(token)
        return entry[0] if entry else None

    def touch(self, token: str) -> None:
        self._purge()
        entry = self._tokens.get(token)
        if entry:
            self._tokens[token] = (entry[0], self._clock())

    def was_expired(self, token: str) -> bool:
        self._purge()
        return bool(token) and token in self._expired

    def revoke(self, token: str) -> None:
        self._tokens.pop(token, None)
        self._expired.pop(token, None)
