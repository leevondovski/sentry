# Generated by Django 5.1.7 on 2025-04-02 19:09

import django
from django.db import migrations, models

import sentry.db.models.fields.bounded
from sentry.new_migrations.migrations import CheckedMigration


class Migration(CheckedMigration):
    # This flag is used to mark that a migration shouldn't be automatically run in production.
    # This should only be used for operations where it's safe to run the migration after your
    # code has deployed. So this should not be used for most operations that alter the schema
    # of a table.
    # Here are some things that make sense to mark as post deployment:
    # - Large data migrations. Typically we want these to be run manually so that they can be
    #   monitored and not block the deploy for a long period of time while they run.
    # - Adding indexes to large tables. Since this can take a long time, we'd generally prefer to
    #   run this outside deployments so that we don't block them. Note that while adding an index
    #   is a schema change, it's completely safe to run the operation after the code has deployed.
    # Once deployed, run these manually via: https://develop.sentry.dev/database-migrations/#migration-deployment

    is_post_deployment = False

    dependencies = [
        ("workflow_engine", "0039_workflow_fire_history_table"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.AlterField(
                    model_name="actionalertruletriggeraction",
                    name="alert_rule_trigger_action",
                    field=sentry.db.models.fields.foreignkey.FlexibleForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="sentry.alertruletriggeraction",
                    ),
                ),
                migrations.AlterField(
                    model_name="alertruledetector",
                    name="alert_rule",
                    field=sentry.db.models.fields.foreignkey.FlexibleForeignKey(
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="sentry.alertrule",
                    ),
                ),
                migrations.AlterField(
                    model_name="alertruledetector",
                    name="rule",
                    field=sentry.db.models.fields.foreignkey.FlexibleForeignKey(
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="sentry.rule",
                    ),
                ),
                migrations.AlterField(
                    model_name="alertruleworkflow",
                    name="alert_rule",
                    field=sentry.db.models.fields.foreignkey.FlexibleForeignKey(
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="sentry.alertrule",
                    ),
                ),
                migrations.AlterField(
                    model_name="alertruleworkflow",
                    name="rule",
                    field=sentry.db.models.fields.foreignkey.FlexibleForeignKey(
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="sentry.rule",
                    ),
                ),
            ],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="alertruledetector",
                    name="rule_or_alert_rule_detector",
                ),
                migrations.RemoveConstraint(
                    model_name="alertruleworkflow",
                    name="rule_or_alert_rule_workflow",
                ),
                migrations.RemoveField(
                    model_name="actionalertruletriggeraction",
                    name="alert_rule_trigger_action",
                ),
                migrations.AlterUniqueTogether(
                    name="alertruledetector",
                    unique_together={("detector", "alert_rule_id"), ("detector", "rule_id")},
                ),
                migrations.AlterUniqueTogether(
                    name="alertruleworkflow",
                    unique_together={("workflow", "alert_rule_id"), ("workflow", "rule_id")},
                ),
                migrations.AddField(
                    model_name="actionalertruletriggeraction",
                    name="alert_rule_trigger_action_id",
                    field=sentry.db.models.fields.bounded.BoundedBigIntegerField(default=0),
                    preserve_default=False,
                ),
                migrations.AddField(
                    model_name="alertruledetector",
                    name="alert_rule_id",
                    field=sentry.db.models.fields.bounded.BoundedBigIntegerField(null=True),
                ),
                migrations.AddField(
                    model_name="alertruledetector",
                    name="rule_id",
                    field=sentry.db.models.fields.bounded.BoundedBigIntegerField(null=True),
                ),
                migrations.AddField(
                    model_name="alertruleworkflow",
                    name="alert_rule_id",
                    field=sentry.db.models.fields.bounded.BoundedBigIntegerField(null=True),
                ),
                migrations.AddField(
                    model_name="alertruleworkflow",
                    name="rule_id",
                    field=sentry.db.models.fields.bounded.BoundedBigIntegerField(null=True),
                ),
                migrations.AddConstraint(
                    model_name="alertruledetector",
                    constraint=models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("alert_rule_id__isnull", True), ("rule_id__isnull", False)),
                            models.Q(("alert_rule_id__isnull", False), ("rule_id__isnull", True)),
                            _connector="OR",
                        ),
                        name="rule_or_alert_rule_detector",
                    ),
                ),
                migrations.AddConstraint(
                    model_name="alertruleworkflow",
                    constraint=models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("alert_rule_id__isnull", True), ("rule_id__isnull", False)),
                            models.Q(("alert_rule_id__isnull", False), ("rule_id__isnull", True)),
                            _connector="OR",
                        ),
                        name="rule_or_alert_rule_workflow",
                    ),
                ),
                migrations.RemoveField(
                    model_name="alertruledetector",
                    name="alert_rule",
                ),
                migrations.RemoveField(
                    model_name="alertruledetector",
                    name="rule",
                ),
                migrations.RemoveField(
                    model_name="alertruleworkflow",
                    name="alert_rule",
                ),
                migrations.RemoveField(
                    model_name="alertruleworkflow",
                    name="rule",
                ),
            ],
        ),
    ]
