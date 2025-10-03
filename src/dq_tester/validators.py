
def validate_catalog(system_catalog, catalog):

    system_test_names = [s.name for s in system_catalog.dq_checks]
    for c in catalog.dq_checks:
        #check if the dq_check name is in the list of system_catalog dq_checks
        if c.name in system_test_names:
            raise ValueError(f'dq_check_name {c.name} is already in the system catalog')


def validate_test_plan(catalog, test_plan):

    for test in test_plan.dq_tests:
         #check if test exists in catalog
        dq_check = catalog.get_dq_check(test.dq_test_name)
        if dq_check is None:
            raise ValueError(f"dq_check_name:{test.dq_test_name} - is not in the master configuration file")
         # Validate SQL Parameters are contained in test
        if dq_check.type=='sql':
            for p in dq_check.sql_params:
                if p not in test.model_extra:
                    #the table_name parameter will be set automatically for files
                    if test_plan.source in ('database','csv') and p=='table_name':
                        pass
                    else:
                        raise ValueError(f"Missing required config key: {p} - in dq_test - {test.dq_test_name}")



