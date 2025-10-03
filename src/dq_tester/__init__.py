"""DQ Tester - A lightweight data quality testing tool."""

from pathlib import Path
from dq_tester.factory import tester_factory

__version__ = "0.4.0"


def get_connections_path(provided_path=None):
    """Get connections path with fallback to default locations"""
    if provided_path:
        return provided_path

    # Check default locations in order
    default_locations = [
        'connections.yaml',  # Current directory
        '~/.dq_tester/connections.yaml',  # User home directory
        '/etc/dq_tester/connections.yaml',  # System-wide (Linux)
    ]

    for location in default_locations:
        path = Path(location).expanduser()
        if path.exists():
            return str(path)

    return None



def run_tests(catalog_path, test_plan_path, connections_path=None):
    """
    Run data quality tests and return results.
    
    Convenience function for simple usage.
    
    Args:
        catalog_path: Path to the catalog YAML file
        test_plan_path: Path to the test plan YAML file
        connections_path: Path to connections YAML file (optional)
        
    Returns:
        list: Test results as dictionaries
    """
    connections_path=get_connections_path(connections_path)
    tester = tester_factory(catalog_path, test_plan_path, connections_path)
    return tester.run_tests()


# For advanced users who want more control
from dq_tester.testers.csv import CsvTester
from dq_tester.testers.database import DatabaseTester
from dq_tester.factory import tester_factory

__all__ = [
    'run_tests',
    'tester_factory',
    'get_connections_path',
    'CsvTester',
    'DatabaseTester',
    '__version__'
]
