import pytest

from sentry.models.environment import Environment
from sentry.testutils.cases import TestCase
from sentry.testutils.helpers import override_options


class GetOrCreateTest(TestCase):
    def test_simple(self):
        project = self.create_project()

        with pytest.raises(Environment.DoesNotExist):
            Environment.get_for_organization_id(project.organization_id, "prod")

        env = Environment.get_or_create(project=project, name="prod")

        assert env.name == "prod"
        assert env.projects.first().id == project.id

        env2 = Environment.get_or_create(project=project, name="prod")

        assert env2.id == env.id

        with self.assertNumQueries(0):
            assert Environment.get_for_organization_id(project.organization_id, "prod").id == env.id

    @override_options({"environmentproject.new_add_project.rollout": 1.0})
    def test_simple_with_new_option(self):
        """
        Same test as test_simple, but with the new option enabled which has refactored
        the get_or_create method.
        Note (vgrozdanic): this test will be removed after the rollout is complete.
        """
        project = self.create_project()

        with pytest.raises(Environment.DoesNotExist):
            Environment.get_for_organization_id(project.organization_id, "prod")

        env = Environment.get_or_create(project=project, name="prod")

        assert env.name == "prod"
        assert env.projects.first().id == project.id

        env2 = Environment.get_or_create(project=project, name="prod")

        assert env2.id == env.id

        with self.assertNumQueries(0):
            assert Environment.get_for_organization_id(project.organization_id, "prod").id == env.id


@pytest.mark.parametrize(
    "val,expected",
    [
        ("42", True),
        ("ok", True),
        ("production", True),
        ("deadbeef", True),
        ("staging.0.1.company", True),
        ("valid_under", True),
        ("spaces ok", True),
        ("no/slashes", False),
        ("no\nnewlines", False),
        ("no\rcarriage", False),
        ("no\fform-feed", False),
    ],
)
def test_valid_name(val, expected):
    assert Environment.is_valid_name(val) == expected
