import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from django.db import router, transaction
from rest_framework.request import Request

from sentry import features
from sentry.locks import locks
from sentry.models.project import Project
from sentry.models.rule import Rule
from sentry.types.actor import Actor
from sentry.utils.locking import UnableToAcquireLock
from sentry.workflow_engine.migration_helpers.issue_alert_migration import (
    IssueAlertMigrator,
    UnableToAcquireLockApiError,
)

logger = logging.getLogger(__name__)


@dataclass
class ProjectRuleCreator:
    name: str
    project: Project
    action_match: str
    actions: Sequence[dict[str, Any]]
    conditions: Sequence[dict[str, Any]]
    frequency: int
    environment: int | None = None
    owner: Actor | None = None
    filter_match: str | None = None
    request: Request | None = None

    def run(self) -> Rule:
        try:
            lock = locks.get(
                f"workflow-engine-project-error-detector:{self.project.id}",
                duration=10,
                name="workflow_engine_issue_alert",
            )
            with lock.acquire(), transaction.atomic(router.db_for_write(Rule)):
                self.rule = self._create_rule()

                if features.has(
                    "organizations:workflow-engine-issue-alert-dual-write",
                    self.project.organization,
                ):
                    # uncaught errors will rollback the transaction
                    workflow = IssueAlertMigrator(
                        self.rule, self.request.user.id if self.request else None
                    ).run()
                    logger.info(
                        "workflow_engine.issue_alert.migrated",
                        extra={"rule_id": self.rule.id, "workflow_id": workflow.id},
                    )
        except UnableToAcquireLock:
            raise UnableToAcquireLockApiError

        return self.rule

    def _create_rule(self) -> Rule:
        kwargs = self._get_kwargs()
        rule = Rule.objects.create(**kwargs)

        return rule

    def _get_kwargs(self) -> dict[str, Any]:
        data = {
            "filter_match": self.filter_match,
            "action_match": self.action_match,
            "actions": self.actions,
            "conditions": self.conditions,
            "frequency": self.frequency,
        }
        _kwargs = {
            "label": self.name,
            "environment_id": self.environment or None,
            "project": self.project,
            "data": data,
            "owner": self.owner,
        }
        return _kwargs
