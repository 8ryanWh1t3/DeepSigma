"""Tests for the Flask extension."""
from __future__ import annotations

import pytest

from deepsigma_middleware.decorator import configure, get_session, reset_session


@pytest.fixture(autouse=True)
def clean_session():
    reset_session()
    yield
    reset_session()


def _skip_no_flask():
    try:
        import flask  # noqa: F401
    except ImportError:
        pytest.skip("Flask not installed")


class TestFlaskDeepSigma:

    def _make_app(self, agent_id="flask-test"):
        _skip_no_flask()
        from flask import Flask
        from deepsigma_middleware.flask_mw import FlaskDeepSigma

        configure(agent_id=agent_id)

        app = Flask(__name__)
        FlaskDeepSigma(app, agent_id=agent_id)

        @app.route("/test")
        def test_route():
            return "ok"

        @app.route("/error")
        def error_route():
            return "fail", 500

        return app

    def test_request_logs_decision(self):
        app = self._make_app()
        with app.test_client() as client:
            resp = client.get("/test")
            assert resp.status_code == 200
        session = get_session()
        assert len(session._episodes) >= 1

    def test_error_request_returns_500(self):
        app = self._make_app(agent_id="flask-error")
        with app.test_client() as client:
            resp = client.get("/error")
            assert resp.status_code == 500

    def test_init_app_deferred(self):
        _skip_no_flask()
        from flask import Flask
        from deepsigma_middleware.flask_mw import FlaskDeepSigma

        ext = FlaskDeepSigma()
        app = Flask(__name__)
        ext.init_app(app)
        assert len(app.before_request_funcs.get(None, [])) >= 1

    def test_extension_sets_agent_id(self):
        app = self._make_app(agent_id="custom-flask")
        with app.test_client() as client:
            client.get("/test")
        session = get_session()
        assert session.agent_id == "custom-flask"
