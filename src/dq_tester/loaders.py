import yaml

from dq_tester.models.catalog import Catalog
from dq_tester.models.test_plan import TestPlan
from dq_tester.models.connections import Connections


def get_catalog(catalog_path):
        with open(catalog_path, "r") as f:
            cat_dict = yaml.safe_load(f)
        catalog = Catalog(**cat_dict)
        return catalog


def get_test_plan(test_plan_path):
        with open(test_plan_path, "r") as f:
            test_plan_dict = yaml.safe_load(f)
        test_plan=TestPlan(**test_plan_dict)
        return test_plan


def get_connections(connections_path):
    with open(connections_path, "r") as f:
        config_dict = yaml.safe_load(f)
    return Connections(**config_dict)







