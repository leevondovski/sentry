import re
from typing import ClassVar, Self
from urllib.parse import unquote

from django.db import IntegrityError, models, router, transaction
from django.utils import timezone

from sentry.backup.scopes import RelocationScope
from sentry.constants import ENVIRONMENT_NAME_MAX_LENGTH, ENVIRONMENT_NAME_PATTERN
from sentry.db.models import (
    BoundedBigIntegerField,
    FlexibleForeignKey,
    Model,
    region_silo_model,
    sane_repr,
)
from sentry.db.models.manager.base import BaseManager
from sentry.options.rollout import in_random_rollout
from sentry.utils import metrics
from sentry.utils.cache import cache
from sentry.utils.hashlib import md5_text
from sentry.utils.rollback_metrics import incr_rollback_metrics

OK_NAME_PATTERN = re.compile(ENVIRONMENT_NAME_PATTERN)


@region_silo_model
class EnvironmentProject(Model):
    __relocation_scope__ = RelocationScope.Organization

    project = FlexibleForeignKey("sentry.Project")
    environment = FlexibleForeignKey("sentry.Environment")
    is_hidden = models.BooleanField(null=True)

    class Meta:
        app_label = "sentry"
        db_table = "sentry_environmentproject"
        unique_together = (("project", "environment"),)


@region_silo_model
class Environment(Model):
    __relocation_scope__ = RelocationScope.Organization

    organization_id = BoundedBigIntegerField()
    projects = models.ManyToManyField("sentry.Project", through=EnvironmentProject)
    name = models.CharField(max_length=64)
    date_added = models.DateTimeField(default=timezone.now)

    objects: ClassVar[BaseManager[Self]] = BaseManager(cache_fields=["pk"])

    class Meta:
        app_label = "sentry"
        db_table = "sentry_environment"
        unique_together = (("organization_id", "name"),)

    __repr__ = sane_repr("organization_id", "name")

    @classmethod
    def is_valid_name(cls, value):
        """Limit length and reject problematic bytes

        If you change the rules here also update the event + monitor check-in ingestion schema in Relay.
        """
        if len(value) > ENVIRONMENT_NAME_MAX_LENGTH:
            return False
        return OK_NAME_PATTERN.match(value) is not None

    @classmethod
    def get_cache_key(cls, organization_id, name):
        return f"env:2:{organization_id}:{md5_text(name).hexdigest()}"

    @classmethod
    def get_name_or_default(cls, name):
        return name or ""

    @classmethod
    def get_for_organization_id(cls, organization_id, name):
        name = cls.get_name_or_default(name)

        cache_key = cls.get_cache_key(organization_id, name)

        env = cache.get(cache_key)
        if env is None:
            env = cls.objects.get(name=name, organization_id=organization_id)
            cache.set(cache_key, env, 3600)

        return env

    @classmethod
    def get_or_create(cls, project, name):
        with metrics.timer("models.environment.get_or_create") as metrics_tags:
            name = cls.get_name_or_default(name)

            cache_key = cls.get_cache_key(project.organization_id, name)

            env = cache.get(cache_key)
            if env is None:
                metrics_tags["cache_hit"] = "false"
                env = cls.objects.get_or_create(name=name, organization_id=project.organization_id)[
                    0
                ]
                cache.set(cache_key, env, 3600)
            else:
                metrics_tags["cache_hit"] = "true"

            env.add_project(project)

            return env

    def add_project(self, project, is_hidden=None):
        cache_key = f"envproj:c:{self.id}:{project.id}"

        if cache.get(cache_key) is None:
            if in_random_rollout("environmentproject.new_add_project.rollout"):
                EnvironmentProject.objects.get_or_create(
                    project=project, environment=self, defaults={"is_hidden": is_hidden}
                )
                # The object already exists, we cache the action to reduce the load on the database.
                cache.set(cache_key, 1, 3600)
            else:
                try:
                    with transaction.atomic(router.db_for_write(EnvironmentProject)):
                        EnvironmentProject.objects.create(
                            project=project, environment=self, is_hidden=is_hidden
                        )
                    cache.set(cache_key, 1, 3600)
                except IntegrityError:
                    incr_rollback_metrics(EnvironmentProject)
                    # We've already created the object, should still cache the action.
                    cache.set(cache_key, 1, 3600)

    @staticmethod
    def get_name_from_path_segment(segment):
        # In cases where the environment name is passed as a URL path segment,
        # the (case-sensitive) string "none" represents the empty string
        # environment name for historic reasons (see commit b09858f.) In all
        # other contexts (incl. request query string parameters), the empty
        # string should be used.
        return unquote(segment) if segment != "none" else ""
