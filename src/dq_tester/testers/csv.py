import duckdb
import csv


from dq_tester.models.catalog import DqCheck, Catalog
from dq_tester.testers.base import DQTester 
from dq_tester.validators import validate_catalog, validate_test_plan


class CsvTester(DQTester):

    def __init__(self, catalog_path, test_plan_path,connections_path):

        super().__init__(catalog_path, test_plan_path,connections_path)
        #validate the catalog
        system_cat= CsvTester.get_system_catalog()
        validate_catalog(system_cat, self.catalog)
        # add system tests to the catalog
        for c in system_cat.dq_checks:
            self.catalog.dq_checks.append(c)
        validate_test_plan(self.catalog, self.test_plan)

        self.connection_name = 'file'
        self.file_table_name='file_table'
        self.tested_object=self.test_plan.file_name
        
        self.con = duckdb.connect(database=':memory:')

    @staticmethod
    def get_system_catalog():
    
        system_checks = [
            DqCheck(name="invalid_records", type="system"),
            DqCheck(name="expected_delimiter", type="system"),
            DqCheck(name="valid_header", type="system"),
            DqCheck(name="total_records", type="system"),
        ]
        return Catalog(dq_checks=system_checks) 



    def _test_delimiter(self):

        test_name = 'expected_delimiter'

        with open(self.test_plan.file_name, "r", newline="") as f:
            sample = f.read(2048)
            sniffer = csv.Sniffer()
            delim=sniffer.sniff(sample).delimiter

            if self.test_plan.delimiter == sniffer.sniff(sample).delimiter:
                status='PASS'
            else:
                status='FAIL'

            self.record_result(test_name=test_name,
                           status=status,
                           result=delim)
            return status

    def _test_header(self):


        if self.test_plan.has_header:

            test_name = 'valid_header'

            with open(self.test_plan.file_name, "r", newline="") as f:
                reader=csv.reader(f, delimiter=self.test_plan.delimiter)
                header=next(reader)        
                expected_columns=[c.name for c in self.test_plan.columns]
            
                if header == expected_columns:
                    status='PASS'
                else:
                    status='FAIL'

                self.record_result(test_name=test_name,
                               status=status,
                               result=header)

                return status

    def schema_validation_tests(self):
        tests=[ self._test_delimiter, self._test_header]
        return "FAIL" if any(test() == "FAIL" for test in tests) else "SUCCESS"


    def _invalid_records(self):

        test_name='invalid_records'
        query = """select count(distinct file_id||'-'||line) 
                 FROM reject_errors"""
        invalid_records=self.con.execute(query).fetchone()[0]

        status=None
        threshold=None

        test=self.test_plan.get_dq_test(test_name)
        if test:
            threshold=test.threshold
            status= self.get_test_status(threshold, invalid_records)

        self.record_result(test_name=test_name,
                           status=status,
                           result=invalid_records,
                           threshold=threshold)



    def _total_records(self):

        test_name = 'total_records'
        query = f"""select count(1) 
                    from {self.file_table_name}"""
        self.total_records=self.con.execute(query).fetchone()[0]

        status=None
        threshold=None

        test=self.test_plan.get_dq_test(test_name)
        if test:
            threshold=test.threshold
            status= self.get_test_status(threshold, self.total_records)

        self.record_result(test_name=test_name,
                           status=status,
                           result=self.total_records,
                           threshold=threshold)





    def data_tests(self):

        try:
            self.con.execute(f"""
                       CREATE TABLE {self.file_table_name} AS
                       SELECT * FROM read_csv('{self.test_plan.file_name}'
                        , header={self.test_plan.has_header}
                       , sep='{self.test_plan.delimiter}'
                       , columns={self.test_plan.columns_as_dict()}
                       , store_rejects = true
              )
                        """)

        except Exception as e:
            raise e

        self._invalid_records()
        self._total_records()

        for t in self.test_plan.dq_tests:
            dq_check=self.catalog.get_dq_check( t.dq_test_name)
            if dq_check.type=='sql':
                sql_params = {}
                for p in dq_check.sql_params:
                    if p=='table_name':
                        sql_params[p]= self.file_table_name
                    else:
                        sql_params[p]=t.model_extra[p]

                sql_str = dq_check.sql.format(**sql_params)

                try:
                    self.con.execute(sql_str)
                    result=self.con.fetchone()[0]
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
        if self.schema_validation_tests()=='SUCCESS':
            self.data_tests()


        return self.test_results

    def __del__(self):
        if hasattr(self, 'con'):
            self.con.close()
