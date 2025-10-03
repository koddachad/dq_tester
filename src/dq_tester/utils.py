import yaml
import duckdb
import os

def csv_to_testplan_yaml(file_name):

    #attempt to open file to see if it exists
    if not os.path.isfile(file_name):
        raise FileNotFoundError(f"The file '{file_name}' was not found.")
    con = duckdb.connect(database=':memory:')
    cursor = con.execute(f"SELECT hasHeader as has_header, delimiter, columns  FROM sniff_csv('{file_name}')")
    columns = [c[0].lower() for c in cursor.description]
    result = cursor.fetchone()
    params = dict(zip(columns, result))
    return yaml.dump(params,sort_keys=False)
