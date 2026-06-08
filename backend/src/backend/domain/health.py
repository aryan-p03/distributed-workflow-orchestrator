from dataclasses import dataclass


@dataclass(frozen=True)
class HealthStatus:
    status: str
    details: dict[str, str]
