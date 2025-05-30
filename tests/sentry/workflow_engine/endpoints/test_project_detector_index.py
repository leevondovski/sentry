from unittest import mock

from sentry.api.serializers import serialize
from sentry.incidents.grouptype import MetricAlertFire
from sentry.incidents.models.alert_rule import AlertRuleDetectionType
from sentry.models.environment import Environment
from sentry.snuba.dataset import Dataset
from sentry.snuba.models import (
    QuerySubscription,
    QuerySubscriptionDataSourceHandler,
    SnubaQuery,
    SnubaQueryEventType,
)
from sentry.testutils.cases import APITestCase
from sentry.testutils.silo import region_silo_test
from sentry.workflow_engine.models import DataCondition, DataConditionGroup, DataSource, Detector
from sentry.workflow_engine.models.data_condition import Condition
from sentry.workflow_engine.registry import data_source_type_registry
from sentry.workflow_engine.types import DetectorPriorityLevel


class ProjectDetectorIndexBaseTest(APITestCase):
    endpoint = "sentry-api-0-project-detector-index"

    def setUp(self):
        super().setUp()
        self.login_as(user=self.user)
        self.environment = Environment.objects.create(
            organization_id=self.organization.id, name="production"
        )
        self.data_condition_group = self.create_data_condition_group(
            organization_id=self.organization.id,
            logic_type=DataConditionGroup.Type.ANY,
        )


@region_silo_test
class ProjectDetectorIndexGetTest(ProjectDetectorIndexBaseTest):
    def test_simple(self):
        detector = self.create_detector(
            project_id=self.project.id, name="Test Detector", type=MetricAlertFire.slug
        )
        detector_2 = self.create_detector(
            project_id=self.project.id, name="Test Detector 2", type=MetricAlertFire.slug
        )
        response = self.get_success_response(self.organization.slug, self.project.slug)
        assert response.data == serialize([detector, detector_2])

    def test_empty_result(self):
        response = self.get_success_response(self.organization.slug, self.project.slug)
        assert len(response.data) == 0


@region_silo_test
class ProjectDetectorIndexPostTest(ProjectDetectorIndexBaseTest):
    method = "POST"

    def setUp(self):
        super().setUp()
        self.valid_data = {
            "name": "Test Detector",
            "detectorType": MetricAlertFire.slug,
            "dataSource": {
                "queryType": SnubaQuery.Type.ERROR.value,
                "dataset": Dataset.Events.name.lower(),
                "query": "test query",
                "aggregate": "count()",
                "timeWindow": 60,
                "environment": self.environment.name,
                "eventTypes": [SnubaQueryEventType.EventType.ERROR.name.lower()],
            },
            "conditionGroup": {
                "id": self.data_condition_group.id,
                "organizationId": self.organization.id,
                "logicType": self.data_condition_group.logic_type,
                "conditions": [
                    {
                        "type": Condition.GREATER,
                        "comparison": 100,
                        "conditionResult": DetectorPriorityLevel.HIGH,
                        "conditionGroupId": self.data_condition_group.id,
                    }
                ],
            },
            "config": {
                "threshold_period": 1,
                "detection_type": AlertRuleDetectionType.STATIC.value,
            },
        }

    def test_missing_group_type(self):
        data = {**self.valid_data}
        del data["detectorType"]
        response = self.get_error_response(
            self.organization.slug,
            self.project.slug,
            **data,
            status_code=400,
        )
        assert response.data == {"detectorType": ["This field is required."]}

    def test_invalid_group_type(self):
        data = {**self.valid_data, "detectorType": "invalid_type"}
        response = self.get_error_response(
            self.organization.slug,
            self.project.slug,
            **data,
            status_code=400,
        )
        assert response.data == {"detectorType": ["Unknown detector type"]}

    def test_incompatible_group_type(self):
        with mock.patch("sentry.issues.grouptype.registry.get_by_slug") as mock_get:
            mock_get.return_value = mock.Mock(detector_settings=None)
            data = {**self.valid_data, "detectorType": "incompatible_type"}
            response = self.get_error_response(
                self.organization.slug,
                self.project.slug,
                **data,
                status_code=400,
            )
            assert response.data == {
                "detectorType": ["Detector type not compatible with detectors"]
            }

    @mock.patch("sentry.workflow_engine.endpoints.validators.base.detector.create_audit_entry")
    def test_valid_creation(self, mock_audit):
        with self.tasks():
            response = self.get_success_response(
                self.organization.slug,
                self.project.slug,
                **self.valid_data,
                status_code=201,
            )

        detector = Detector.objects.get(id=response.data["id"])
        assert response.data == serialize([detector])[0]
        assert detector.name == "Test Detector"
        assert detector.type == MetricAlertFire.slug
        assert detector.project_id == self.project.id

        # Verify data source
        data_source = DataSource.objects.get(detector=detector)
        assert data_source.type == data_source_type_registry.get_key(
            QuerySubscriptionDataSourceHandler
        )
        assert data_source.organization_id == self.organization.id

        # Verify query subscription
        query_sub = QuerySubscription.objects.get(id=int(data_source.source_id))
        assert query_sub.project == self.project
        assert query_sub.snuba_query.type == SnubaQuery.Type.ERROR.value
        assert query_sub.snuba_query.dataset == Dataset.Events.value
        assert query_sub.snuba_query.query == "test query"
        assert query_sub.snuba_query.aggregate == "count()"
        assert query_sub.snuba_query.time_window == 3600
        assert query_sub.snuba_query.environment == self.environment
        assert query_sub.snuba_query.event_types == [SnubaQueryEventType.EventType.ERROR]

        # Verify condition group and conditions
        condition_group = detector.workflow_condition_group
        assert condition_group
        assert condition_group.logic_type == DataConditionGroup.Type.ANY
        assert condition_group.organization_id == self.organization.id

        conditions = list(DataCondition.objects.filter(condition_group=condition_group))
        assert len(conditions) == 1
        condition = conditions[0]
        assert condition.type == Condition.GREATER
        assert condition.comparison == 100
        assert condition.condition_result == DetectorPriorityLevel.HIGH

        # Verify audit log
        mock_audit.assert_called_once_with(
            request=mock.ANY,
            organization=self.organization,
            target_object=detector.id,
            event=mock.ANY,
            data=detector.get_audit_log_data(),
        )

    def test_missing_required_field(self):
        response = self.get_error_response(
            self.organization.slug,
            self.project.slug,
            status_code=400,
        )
        assert response.data == {"detectorType": ["This field is required."]}

    def test_missing_name(self):
        data = {**self.valid_data}
        del data["name"]
        response = self.get_error_response(
            self.organization.slug,
            self.project.slug,
            **data,
            status_code=400,
        )
        assert response.data == {"name": ["This field is required."]}
