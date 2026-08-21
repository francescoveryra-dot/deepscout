"""Hosted tenant isolation — UUID secrecy is not authorization."""

from __future__ import annotations

from uuid import uuid4

import pytest
from deepscout_core.domain.schemas import ResearchRunCreate
from deepscout_core.settings import Settings
from deepscout_persistence.identity import create_session, upsert_oauth_principal
from deepscout_persistence.session import get_session_factory
from deepscout_persistence.store import ResearchStore
from fastapi.testclient import TestClient
from tests.db_helpers import database_url

pytestmark = pytest.mark.postgres


@pytest.fixture
def hosted_client(monkeypatch, postgres_ready):
    monkeypatch.setenv("DEEPSCOUT_DEPLOYMENT_MODE", "hosted")
    monkeypatch.setenv("SESSION_SECRET", "session-secret-for-tests-not-used-directly")
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "0" * 32)
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_ID", "test-github-id")
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_SECRET", "test-github-secret")
    from deepscout_api.app import app

    return TestClient(app)


def _session():
    return get_session_factory(database_url())()


def _user(session, name: str):
    principal = upsert_oauth_principal(
        session,
        provider="github",
        provider_account_id=f"{name}-{uuid4().hex[:8]}",
        display_name=name,
        email=None,
        email_verified=False,
        avatar_url=None,
    )
    token = create_session(session, principal.id)
    session.commit()
    return principal, token


def test_user_b_cannot_read_user_a_run(hosted_client) -> None:
    session = _session()
    store = ResearchStore(session)
    settings = Settings(_env_file=None)
    user_a, token_a = _user(session, "A")
    user_b, token_b = _user(session, "B")
    run = store.create_run(
        ResearchRunCreate(goal="User A private research"),
        settings,
        owner_principal_id=user_a.id,
    )
    session.commit()
    try:
        denied = hosted_client.get(
            f"/api/v1/research-runs/{run.id}", cookies={"ds_session": token_b}
        )
        assert denied.status_code == 404
        allowed = hosted_client.get(
            f"/api/v1/research-runs/{run.id}", cookies={"ds_session": token_a}
        )
        assert allowed.status_code == 200
        assert hosted_client.get(f"/api/v1/research-runs/{run.id}").status_code == 404
    finally:
        from deepscout_persistence.identity import delete_principal_data

        delete_principal_data(session, user_a.id)
        delete_principal_data(session, user_b.id)
        session.commit()
        session.close()


def test_demo_is_read_only_for_anonymous(hosted_client) -> None:
    session = _session()
    store = ResearchStore(session)
    settings = Settings(_env_file=None)
    user_a, _token = _user(session, "DemoOwner")
    demo = store.create_run(
        ResearchRunCreate(goal="Published demo"),
        settings,
        owner_principal_id=user_a.id,
        is_public_demo=True,
        public_slug=f"demo-{uuid4().hex[:8]}",
    )
    session.commit()
    try:
        assert hosted_client.get(f"/api/v1/research-runs/{demo.id}").status_code == 200
        execute = hosted_client.post(f"/api/v1/research-runs/{demo.id}/execute")
        assert execute.status_code in {401, 403, 404}
    finally:
        from deepscout_persistence.identity import delete_principal_data

        delete_principal_data(session, user_a.id)
        session.commit()
        session.close()


def test_open_redirect_rejected() -> None:
    from deepscout_api.access import safe_next_path

    assert safe_next_path("https://evil.test", "/") == "/"
    assert safe_next_path("//evil.test", "/") == "/"
    assert safe_next_path("/account", "/,/account") == "/account"
