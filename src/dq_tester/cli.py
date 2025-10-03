from pydantic import ValidationError
import operator
import argparse
import yaml
import os
from pathlib import Path


from dq_tester.loaders import get_catalog, get_test_plan
from dq_tester.validators import validate_catalog, validate_test_plan
from dq_tester.factory import tester_factory
from dq_tester.utils import csv_to_testplan_yaml
from dq_tester.testers.csv import CsvTester
from dq_tester import get_connections_path



def validate_catalog_only(catalog_path):
    catalog = get_catalog(catalog_path)


def run_tests(catalog_path, test_plan_path, connections_path=None):
    
    connections_path=get_connections_path(connections_path)
    tester = tester_factory(catalog_path=catalog_path, 
                            test_plan_path=test_plan_path,
                            connections_path=connections_path)
    tester.run_tests()
    tester.print_results()


def validate_config_files(catalog_path, test_plan_path):

    catalog = get_catalog(catalog_path)
    test_plan= get_test_plan(test_plan_path)

    if test_plan.source=='csv': 
        system_catalog=CsvTester.get_system_catalog()   

    #validates that the catalog does not have any tests 
    #that share a name with tests in the system catalog
    validate_catalog(system_catalog, catalog)
    # add system tests to the catalog
    for c in system_catalog.dq_checks:
        catalog.dq_checks.append(c)
    #validate that the test_plan is configured correctly
    validate_test_plan(catalog, test_plan)




def main():
    parser = argparse.ArgumentParser(description='Validate and run tests on configuration files')
    parser.add_argument('-c', '--catalog-path', type=str,  help='Path to the catalog file')
    parser.add_argument('-t', '--test-plan-path', type=str, help='Path to the test plan file')
    parser.add_argument('--csv-path', type=str, help='Path to the csv file')
    parser.add_argument('-a', '--action', type=str, choices=['validate',  'run','csv-to-yaml'], 
                        required=True, help='Action to perform:' 
                        'validate, '
                        'run, ' 
                        'csv-to-yaml')
   
    parser.add_argument('--connections-path', type=str, 
                    help='Path to connections config. Defaults to first found: '
                         '1) ./connections.yaml, '
                         '2) ~/.dq_tester/connections.yaml, '
                         '3) /etc/dq_tester/connections.yaml')

    args = parser.parse_args()
    
    if args.action == 'validate':
        if not args.catalog_path:
            parser.error("--catalog-path is required for validate action")
        if args.test_plan_path:
            try:
                validate_config_files(args.catalog_path, args.test_plan_path)
                print("Validation completed successfully")
            except FileNotFoundError as e:
                print(e)
            except yaml.YAMLError as e:
                print('Invalid YAML syntax:',e)
            except ValidationError as e:
                for err in e.errors():
                    print(f"{err['loc']}: {err['msg']} ({err['type']})")
            except ValueError as e:
                print(e)
        else:
            try:
                validate_catalog_only(args.catalog_path)
                print("Catalog validation completed successfully")
            except FileNotFoundError:
                print(f'File {args.catalog_path} not found')
            except yaml.YAMLError as e:
                print('Invalid YAML syntax:',e)
            except ValidationError as e:
                for err in e.errors():
                    print(f"{err['loc']}: {err['msg']} ({err['type']})")
            except ValueError as e:
                print(e)


    elif args.action == 'run':
        if not args.catalog_path:
            parser.error("--catalog-path is required for run action")
        if not args.test_plan_path:
            parser.error("--test-plan-path is required for run action")
        try:
            run_tests(args.catalog_path, args.test_plan_path, args.connections_path)
            print("Tests completed")
        except FileNotFoundError as e:
            print(e)
        except yaml.YAMLError as e:
            print('Invalid YAML syntax:',e)
        except ValidationError as e:
            for err in e.errors():
                print(f"{err['loc']}: {err['msg']} ({err['type']})")
        except ValueError as e:
            print(e)    

    elif args.action == 'csv-to-yaml':

        if not args.csv_path:
            parser.error("--csv-path is required for csv-to-yaml action")
        try:
            y=csv_to_testplan_yaml(args.csv_path)
            print(y)
        except FileNotFoundError as e:
                print(e)


if __name__ == '__main__':
    main()











