from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal


class WorkflowTemplateError(ValueError):
    """Raised when a workflow template request is invalid."""


@dataclass(frozen=True)
class WorkflowTaskTemplate:
    sequence: int
    name: str
    task_type: str
    input_payload: dict[str, str]


@dataclass(frozen=True)
class WorkflowTemplatePlan:
    workflow_name: str
    tasks: tuple[WorkflowTaskTemplate, ...]


@dataclass(frozen=True)
class WorkflowTemplateField:
    key: str
    label: str
    placeholder: str
    control: Literal["input", "textarea"] = "input"


@dataclass(frozen=True)
class WorkflowTemplateDefinition:
    label: str
    description: str
    fields: tuple[WorkflowTemplateField, ...]
    default_name: Callable[[dict[str, str]], str]
    build_tasks: Callable[[dict[str, str]], tuple[WorkflowTaskTemplate, ...]]

    @property
    def required_fields(self) -> tuple[str, ...]:
        return tuple(field.key for field in self.fields)


def _text_analysis_tasks(values: dict[str, str]) -> tuple[WorkflowTaskTemplate, ...]:
    return (
        WorkflowTaskTemplate(
            sequence=1,
            name="Analyze submitted text",
            task_type="text_analyze",
            input_payload={"text": values["text"]},
        ),
    )


def _csv_summary_tasks(values: dict[str, str]) -> tuple[WorkflowTaskTemplate, ...]:
    return (
        WorkflowTaskTemplate(
            sequence=1,
            name="Summarize submitted CSV",
            task_type="csv_process",
            input_payload={"csv_text": values["csv_text"]},
        ),
    )


WORKFLOW_TEMPLATES: dict[str, WorkflowTemplateDefinition] = {
    "text_analysis": WorkflowTemplateDefinition(
        label="Text Analysis",
        description="Counts characters, words, and sentences in submitted text.",
        fields=(
            WorkflowTemplateField(
                key="text",
                label="Text",
                placeholder="Paste text to analyze",
                control="textarea",
            ),
        ),
        default_name=lambda values: "Text analysis",
        build_tasks=_text_analysis_tasks,
    ),
    "csv_summary": WorkflowTemplateDefinition(
        label="CSV Summary",
        description="Counts rows and columns in submitted CSV data.",
        fields=(
            WorkflowTemplateField(
                key="csv_text",
                label="CSV Data",
                placeholder="name,score\nalpha,10",
                control="textarea",
            ),
        ),
        default_name=lambda values: "CSV summary",
        build_tasks=_csv_summary_tasks,
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
