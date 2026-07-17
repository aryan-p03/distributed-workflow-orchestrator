from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass


class WorkflowTemplateError(ValueError):
    """Raised when a workflow template request is invalid."""


@dataclass(frozen=True)
class WorkflowTaskTemplate:
    sequence: int
    name: str
    task_type: str


@dataclass(frozen=True)
class WorkflowTemplatePlan:
    workflow_name: str
    tasks: tuple[WorkflowTaskTemplate, ...]


@dataclass(frozen=True)
class WorkflowTemplateDefinition:
    required_fields: tuple[str, ...]
    default_name: Callable[[dict[str, str]], str]
    build_tasks: Callable[[dict[str, str]], tuple[WorkflowTaskTemplate, ...]]


def _document_processing_tasks(values: dict[str, str]) -> tuple[WorkflowTaskTemplate, ...]:
    document_name = values["document_name"]
    destination_uri = values["destination_uri"]
    return (
        WorkflowTaskTemplate(1, f"Fetch {document_name}", "document.fetch"),
        WorkflowTaskTemplate(2, f"Transform {document_name}", "document.transform"),
        WorkflowTaskTemplate(3, f"Publish to {destination_uri}", "document.publish"),
    )


def _release_pipeline_tasks(values: dict[str, str]) -> tuple[WorkflowTaskTemplate, ...]:
    service_name = values["service_name"]
    environment = values["environment"]
    return (
        WorkflowTaskTemplate(1, f"Validate {service_name}", "release.validate"),
        WorkflowTaskTemplate(2, f"Deploy to {environment}", "release.deploy"),
        WorkflowTaskTemplate(3, f"Smoke test {service_name}", "release.smoke_test"),
    )


WORKFLOW_TEMPLATES: dict[str, WorkflowTemplateDefinition] = {
    "document_processing": WorkflowTemplateDefinition(
        required_fields=("document_name", "source_uri", "destination_uri"),
        default_name=lambda values: f"Process {values['document_name']}",
        build_tasks=_document_processing_tasks,
    ),
    "release_pipeline": WorkflowTemplateDefinition(
        required_fields=("service_name", "release_version", "environment"),
        default_name=lambda values: f"Deploy {values['service_name']} {values['release_version']}",
        build_tasks=_release_pipeline_tasks,
    ),
}


def resolve_workflow_template(
    template_name: str,
    payload: Mapping[str, object],
) -> WorkflowTemplatePlan:
    definition = WORKFLOW_TEMPLATES.get(template_name)
    if definition is None:
        raise WorkflowTemplateError(f"Unsupported workflow template: {template_name}")

    values = _validate_payload(payload, definition)
    workflow_name = values.get("workflow_name") or definition.default_name(values)

    return WorkflowTemplatePlan(
        workflow_name=workflow_name,
        tasks=definition.build_tasks(values),
    )


def _validate_payload(
    payload: Mapping[str, object],
    definition: WorkflowTemplateDefinition,
) -> dict[str, str]:
    allowed_fields = set(definition.required_fields) | {"workflow_name"}
    unexpected_fields = sorted(set(payload) - allowed_fields)
    if unexpected_fields:
        raise WorkflowTemplateError(
            "Unexpected workflow template fields: " + ", ".join(unexpected_fields)
        )

    values: dict[str, str] = {}
    for field_name in definition.required_fields:
        values[field_name] = _normalize_string(payload, field_name)

    if "workflow_name" in payload:
        values["workflow_name"] = _normalize_string(payload, "workflow_name")

    return values


def _normalize_string(payload: Mapping[str, object], field_name: str) -> str:
    raw_value = payload.get(field_name)
    if not isinstance(raw_value, str):
        raise WorkflowTemplateError(f"Field '{field_name}' must be a non-empty string")

    value = raw_value.strip()
    if not value:
        raise WorkflowTemplateError(f"Field '{field_name}' must be a non-empty string")

    return value
