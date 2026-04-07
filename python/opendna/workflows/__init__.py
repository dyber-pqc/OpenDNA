"""Workflow YAML engine - declarative reproducible pipelines.

Example:
    from opendna.workflows import run_workflow

    result = run_workflow("my_pipeline.yaml")
"""

from opendna.workflows.engine import run_workflow, parse_workflow, WorkflowResult

__all__ = ["run_workflow", "parse_workflow", "WorkflowResult"]
