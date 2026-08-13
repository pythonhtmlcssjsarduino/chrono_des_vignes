from flask.testing import FlaskClient


def test_home(client: FlaskClient):
    res2 = client.get("/")
    assert res2.status_code == 200, "home page should be accessible"
