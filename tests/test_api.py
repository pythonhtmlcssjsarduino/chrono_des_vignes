from typing import Any
from unittest.mock import Mock, patch

from chrono_des_vignes.api import ApiBlueprint


class DummyUser:
    def __init__(
        self,
        is_authenticated: bool = True,
        admin: bool = False,
        creations: Any | None = None,
    ):
        self.is_authenticated: bool = is_authenticated
        self.admin: bool = admin
        self.creations: Any | Mock = creations or Mock()


def test_login_required_returns_login_error_for_unauthenticated_user():
    api = ApiBlueprint(
        "test", ["admin_required"], error_callback=lambda self, err: {"err": err}
    )

    @api.route("/test")
    def view_login():
        return {"ok": True}

    with patch(
        "chrono_des_vignes.api.current_user", new=DummyUser(is_authenticated=False)
    ):
        assert view_login() == {"err": "login"}


def test_admin_required_returns_admin_error_for_non_admin_user():
    api = ApiBlueprint(
        "test", ["admin_required"], error_callback=lambda self, err: {"err": err}
    )

    @api.route("/test")
    def view_admin():
        return {"ok": True}

    with patch(
        "chrono_des_vignes.api.current_user",
        new=DummyUser(is_authenticated=True, admin=False),
    ):
        assert view_admin() == {"err": "admin"}


def test_admin_required_returns_event_error_when_user_has_no_event():
    api = ApiBlueprint(
        "test", ["admin_required"], error_callback=lambda self, err: {"err": err}
    )
    creations = Mock()
    creations.filter_by.return_value.first.return_value = None

    @api.route("/test/<int:event_id>")
    def view_admin_event(event_id: int):
        return {"ok": True}

    with patch(
        "chrono_des_vignes.api.current_user",
        new=DummyUser(is_authenticated=True, admin=True, creations=creations),
    ):
        assert view_admin_event(event_id=1) == {"err": "event"}


def test_admin_required_allows_admin_with_event():
    api = ApiBlueprint(
        "test", ["admin_required"], error_callback=lambda self, err: {"err": err}
    )
    creations = Mock()
    creations.filter_by.return_value.first.return_value = True

    @api.route("/test/<int:event_id>")
    def view_admin_event_ok(event_id: int):  # pyright: ignore[reportUnusedParameter]
        return {"ok": True}

    with patch(
        "chrono_des_vignes.api.current_user",
        new=DummyUser(is_authenticated=True, admin=True, creations=creations),
    ):
        assert view_admin_event_ok(event_id=1) == {"ok": True}
