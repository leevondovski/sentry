from __future__ import annotations

from django.db import IntegrityError, models, router, transaction
from django.utils import timezone

from sentry.backup.scopes import RelocationScope
from sentry.db.models import (
    BoundedBigIntegerField,
    Model,
    control_silo_model,
    region_silo_model,
    sane_repr,
)
from sentry.silo.base import SiloMode
from sentry.utils.rollback_metrics import incr_rollback_metrics


class TombstoneBase(Model):
    """
    Records a hard deletion so that the delete action can be propagated
    between regions. Subclasses provide specialized table names for each
    direction data needs to flow in.

    Tombstones are generally created by outbox receievers. Once
    created, tombstones are propagated between regions with RPC (coming soon)
    """

    class Meta:
        abstract = True

    __relocation_scope__ = RelocationScope.Excluded

    table_name = models.CharField(max_length=48, null=False)
    object_identifier = BoundedBigIntegerField(null=False)
    created_at = models.DateTimeField(null=False, default=timezone.now)

    @staticmethod
    def class_for_silo_mode(silo_mode: SiloMode) -> type[TombstoneBase] | None:
        if silo_mode == SiloMode.REGION:
            return RegionTombstone
        if silo_mode == SiloMode.CONTROL:
            return ControlTombstone
        return None

    @classmethod
    def record_delete(cls, table_name: str, identifier: int):
        try:
            with transaction.atomic(router.db_for_write(cls)):
                cls.objects.create(table_name=table_name, object_identifier=identifier)
        except IntegrityError:
            incr_rollback_metrics(cls)
            pass


@region_silo_model
class RegionTombstone(TombstoneBase):
    class Meta:
        app_label = "sentry"
        db_table = "sentry_regiontombstone"
        indexes = [
            models.Index(
                fields=["table_name", "object_identifier"],
            )
        ]

    __repr__ = sane_repr("id", "table_name", "object_identifier")


@control_silo_model
class ControlTombstone(TombstoneBase):
    class Meta:
        app_label = "sentry"
        db_table = "sentry_controltombstone"
        indexes = [
            models.Index(
                fields=["table_name", "object_identifier"],
            )
        ]

    __repr__ = sane_repr("id", "table_name", "object_identifier")
