import sys
from os.path import abspath, dirname
from threading import Thread

import pytest
from fakeredis import TcpFakeServer

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from chrono_des_vignes import create_app, db


@pytest.fixture
def app():
    app = create_app("test")

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def redis_sse():
    server_address = ("127.0.0.1", 8500)
    server = TcpFakeServer(server_address, server_type="redis")
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()

    yield

    server.shutdown()
    server.server_close()
    t.join()
