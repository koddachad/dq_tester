from datetime import datetime, timezone
from tabulate import tabulate
import operator
from dq_tester.loaders import get_catalog, get_test_plan, get_connections
from pathlib import Path
import duckdb
import re

class DQTester:

    def __init__(self, catalog_path, test_plan_path,connections_path):

        self.catalog = get_catalog(catalog_path)
        self.test_plan= get_test_plan(test_plan_path)
        self.connections=None
        self.tested_object=None
        self.connection_name=None
        self.results_con=None
        self.test_results=[]
        results_db_config=None

        if connections_path:
            self.connections=get_connections(connections_path)

        if self.connections:
            results_db_config=self.connections.get_connection(name='results_db')

            if results_db_config:

                self._setup_results_database(results_db_config)

    def _setup_results_database(self, conn_config):

        if conn_config.driver.upper() != 'DUCKDB':
            raise ValueError(f"results_db must use DuckDB driver, got: {conn_config.driver}")

        db_path = Path(conn_config.database)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.results_con = duckdb.connect(str(db_path))
        self._create_results_table()



    def _create_results_table(self):

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS test_results (
            connection_name VARCHAR,
            tested_object VARCHAR,
            test_ts TIMESTAMP,
            dq_test_name VARCHAR,
            status VARCHAR,
            test_parameters VARCHAR,
            threshold_op VARCHAR,
            threshold_val VARCHAR,
            test_sql VARCHAR,
            error VARCHAR
        )
        """
        self.results_con.execute(create_table_sql)        




    def _persist_result(self, result_record):

        insert_sql = """
            INSERT INTO test_results 
                 (connection_name, 
                  tested_object, 
                  test_ts, 
                  dq_test_name, 
                  status, 
                  test_parameters, 
                  threshold_op, 
                  threshold_val, 
                  test_sql, 
                  error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        self.results_con.execute(insert_sql, [
                result_record['connection_name'],
                result_record['tested_object'],
                result_record['test_ts'],
                result_record['dq_test_name'],
                result_record['status'],
                result_record['test_parameters'],
                result_record['threshold_op'],
                result_record['threshold_val'],
                result_record['test_sql'],
                result_record['error']
               ])
        self.results_con.commit()        




    def run_tests(self):
        raise NotImplementedError('Subclasses must implement run_tests().')


    def schema_validation_tests(self):
        raise NotImplementedError('Subclasses must implement schema_validation()')

    def get_test_status(self,threshold, result):

        ops = {
            '>': operator.gt,
            '>=': operator.ge,
            '==': operator.eq,
            '<=': operator.le,
            '<': operator.lt,
        }

        op=threshold.operator
        v=threshold.value

        # convert to percentage  percentage type
        if threshold.type == 'pct':
            if self.total_records is None or self.total_records == 0:
                raise ValueError('total_records must be provided and > 0 for pct type')
            result = round((result / self.total_records) * 100, 2)

        status = 'PASS' if ops[op](result, v) else 'FAIL'
        return status

    def record_result(self, test_name, status,result, test_parameters = None, threshold = None, test_sql=None, error=None  ):


        threshold_op=None
        threshold_val=None

        if threshold:
            threshold_op=threshold.operator
            threshold_val=threshold.value

        if test_parameters:

            test_parameters =  str({k: str(v) for k, v in test_parameters.items()})


        result_record = {   'connection_name':self.connection_name,
                              'tested_object':self.tested_object,
                              'test_ts': datetime.now(timezone.utc),
                              'dq_test_name':test_name,
                              'status':status,
                              'result':result,
                              'test_parameters':test_parameters,
                              'threshold_op':threshold_op,
                              'threshold_val':threshold_val,
                              'test_sql':test_sql,
                              'error':error}

        self.test_results.append(result_record )

        if self.results_con:
            self._persist_result(result_record)


    def print_results(self):


        headers = ['connection_name',
                   'tested_object',
                   'test_ts',
                   'dq_test_name',
                   'status',
                   'result',
                   'test_parameters',
                   'threshold_op',
                   'threshold_val',
                   'test_sql',
                   'error'
                 ]

        rows = []
        for rec in self.test_results:
            row = []
            for key in headers:
                val = rec.get(key)
                if val is None:
                    val=''
                if hasattr(val, 'isoformat'):  # handles datetime
                    val = val.replace(microsecond=0).isoformat()
                    val = val.split("+")[0]
                row.append(val)
            rows.append(row)

        print(tabulate(rows, headers=headers, tablefmt='grid', maxcolwidths=[20]*len(headers)))


