import pyodbc

from dq_tester.models.catalog import DqCheck, Catalog
from dq_tester.testers.base import DQTester 
from dq_tester.validators import validate_catalog, validate_test_plan


class DatabaseTester(DQTester):

    def __init__(self, catalog_path, test_plan_path,connections_path):

        super().__init__(catalog_path, test_plan_path,connections_path)
        #validate the catalog
        system_cat= DatabaseTester.get_system_catalog()
        validate_catalog(system_cat, self.catalog)
        # add system tests to the catalog
        for c in system_cat.dq_checks:
            self.catalog.dq_checks.append(c)

        validate_test_plan(self.catalog, self.test_plan)
        conn_config=self.connections.get_connection(self.test_plan.connection_name)
        conn_str = (
            f"Driver={{{conn_config.driver}}};"
            f"Server={conn_config.server};"
            f"Database={conn_config.database};"
            f"Uid={conn_config.username};"
            f"Pwd={conn_config.password};"
            )

        self.connection_name=self.test_plan.connection_name
        self.tested_object=self.test_plan.table_name
        self.con = pyodbc.connect(conn_str)
    @staticmethod
    def get_system_catalog():
    
        system_checks = [
            DqCheck(name="total_records", type="system")
        ]
        return Catalog(dq_checks=system_checks) 




    def _total_records(self):

        test_name = 'total_records'
        query = f"""SELECT COUNT(1) 
                    FROM {self.test_plan.table_name}"""
    
        status = None
        threshold = None
        result = None
        error = None
    
        try:
            result = self.con.execute(query).fetchone()[0]
            self.total_records = result
        
            test = self.test_plan.get_dq_test(test_name)
            if test:
                threshold = test.threshold
                status = self.get_test_status(threshold, result)
    
        except Exception as e:
            status = 'ERROR'
            error = str(e)
    
        self.record_result(
            test_name=test_name,
            status=status,
            result=result,
            test_parameters=None,
            threshold=threshold,
            test_sql=query,
            error=error
        )




    def data_tests(self):

        self._total_records()

        for t in self.test_plan.dq_tests:
            dq_check=self.catalog.get_dq_check( t.dq_test_name)
            if dq_check.type=='sql':
                sql_params = {}
                for p in dq_check.sql_params:

                    if p=='table_name':
                        sql_params[p]= self.test_plan.table_name
                    else:
                        sql_params[p]=t.model_extra[p]

                sql_str = dq_check.sql.format(**sql_params)

                try:
                    cur=self.con.execute(sql_str)
                    result=cur.fetchone()[0]
                    status = self.get_test_status(t.threshold, result)
                except Exception as e:
                    self.record_result(test_name=t.dq_test_name,
                                       status='ERROR', 
                                       result=None, 
                                       test_parameters = t.model_extra, 
                                       threshold = t.threshold, 
                                       test_sql=sql_str,
                                       error=str(e))
                    continue

                self.record_result(test_name=t.dq_test_name,
                                   status=status, 
                                   result=result, 
                                   test_parameters = t.model_extra, 
                                   threshold = t.threshold, 
                                   test_sql=sql_str)



    def run_tests(self):
            
        self.data_tests()
                
        return self.test_results

    def __del__(self):
        if hasattr(self, 'con'):
            self.con.close()


