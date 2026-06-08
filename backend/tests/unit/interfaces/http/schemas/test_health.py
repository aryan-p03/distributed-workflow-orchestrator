from backend.domain.health import HealthStatus
from backend.interfaces.http.schemas.health import HealthResponse


def test_health_response_from_domain() -> None:
    domain_status = HealthStatus(status="ok", details={})
    response = HealthResponse.model_validate(domain_status)

    assert response.status == "ok"
    assert response.details == {}
    assert response.model_dump() == {"status": "ok", "details": {}}
