from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.infrastructure.db.models import User
from tests.conftest import AuthenticatedClient, InMemoryRedis
from tests.factories import create_task, create_task_log, create_user, create_workflow


def test_authenticated_client_can_access_me(authenticated_client: AuthenticatedClient) -> None:
    response = authenticated_client.client.get(
        "/auth/me",
        headers=authenticated_client.auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == authenticated_client.user.email
    assert payload["username"] == authenticated_client.user.username


def test_isolated_redis_fixture_resets_state(isolated_redis: InMemoryRedis) -> None:
    assert isolated_redis.get("key") is None
    isolated_redis.set("key", "value")
    assert isolated_redis.get("key") == "value"


def test_factories_create_related_records(db_session: Session) -> None:
    user = create_user(db_session, email="factory@example.com", username="factory")
    workflow = create_workflow(db_session, user_id=user.id, name="Factory workflow")
    task = create_task(db_session, workflow_id=workflow.id, name="Factory task")
    task_log = create_task_log(db_session, task_id=task.id, message="Created by factory")
    db_session.commit()

    users = db_session.execute(select(User)).scalars().all()

    assert len(users) == 1
    assert workflow.user_id == user.id
    assert task.workflow_id == workflow.id
    assert task_log.task_id == task.id
