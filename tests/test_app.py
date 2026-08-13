from flask import Flask, session

from chrono_des_vignes import get_locale, lang_url_for


def test_create_app_loads_test_config(app: Flask):

    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite")  # pyright: ignore[reportUnknownMemberType]
    assert "api" in app.blueprints


def test_get_locale_prefers_session_value(app: Flask):

    with app.test_request_context("/", headers={"Accept-Language": "de"}):
        session["lang"] = "fr"
        assert get_locale() == "fr"


def test_get_locale_uses_accept_language_when_no_session(app: Flask):

    with app.test_request_context("/", headers={"Accept-Language": "de"}):
        assert get_locale() == "de"


def test_lang_url_for_static_endpoint_uses_url_for(app: Flask):

    with app.test_request_context():
        result = lang_url_for("static", lang="fr", filename="style.css")
        assert "/static" in result
