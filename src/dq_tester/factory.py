from dq_tester.loaders import get_test_plan
from dq_tester.testers.csv import CsvTester
from dq_tester.testers.database import DatabaseTester

def tester_factory(catalog_path, test_plan_path,connections_path):

    TESTER_MAP = {
         'csv': CsvTester,
         'database': DatabaseTester
     }

    plan=get_test_plan(test_plan_path)

    tester_class = TESTER_MAP.get(plan.source)

    if not tester_class:

        raise ValueError(f"Unknown source type: {plan.source}")

    return tester_class(catalog_path, test_plan_path,connections_path)
