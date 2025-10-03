# DQ Tester

A lightweight, simple data quality testing tool for CSV files and databases.

## Overview

DQ Tester allows you to define data quality checks in SQL and organize them into reusable test catalogs. Execute tests against CSV files or databases, and monitor results through an interactive Streamlit dashboard.

**Key Features:**
- 📝 Simple YAML configuration for tests and catalogs
- 🗄️ Support for CSV files and databases (via ODBC)
- 📊 Built-in Streamlit dashboard for monitoring test results
- 🔍 Customizable SQL-based data quality checks
- 💾 Test results stored in DuckDB for analysis

## Requirements

- Python 3.9+
- ODBC driver for your database (currently tested with PostgreSQL)

## Installation

```bash
pip install dq_tester
```

## Setup with Claude

To use DQ Tester with Claude:

1. Upload `prompt_custom_instructions.txt` as a project instruction file
2. Upload the following example files to your project:
   - `examples/catalog.yaml`
   - `examples/connections.yaml`
   - `examples/db_test_plan.yaml`
   - `examples/file_test_plan.yaml`

Claude will use these files to help you create and manage data quality tests.

## Python API

DQ Tester can be used directly in Python for custom workflows and integrations:

```python
import dq_tester
import sys

results = dq_tester.run_tests('examples/catalog.yaml', 'examples/file_test_plan.yaml')
failed = [r for r in results if r['status'] == 'FAIL']

if failed:
    print(f"{len(failed)} tests failed")
    sys.exit(1)
print("All tests passed")
```

## Quick Start

### 1. Configure Database Connections

Create a `connections.yaml` file:

```yaml
connections:
  - name: sample_db
    driver: "PostgreSQL"
    server: "myserver"
    database: "demo_source"
    username: "user"
    password: "password"

  - name: results_db  # Required: results stored here
    driver: "DuckDB"
    database: "./results/test_results.duckdb"
```

**Note:** The `results_db` connection is required for storing test results.

### 2. Create a Catalog of DQ Checks

Create a `catalog.yaml` file defining reusable data quality checks:

```yaml
dq_checks:
  - name: null_values
    type: sql
    sql: |
      select count(1)
      from {table_name}
      where {column_name} is null
  
  - name: duplicate_key
    type: sql
    sql: |
      select count(1)
      from (
        select {key_cols}
        from {table_name}
        group by {key_cols}
        having count(1) > 1
      ) t1
  
  - name: invalid_email_duckdb
    type: sql
    sql: |
      select count(1)
      from {table_name}
      WHERE NOT REGEXP_FULL_MATCH(
          {column_name},
          '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{{2,}}$'
      )
```

**Parameters in SQL:** Use `{parameter_name}` in your SQL to define parameters. These must be provided in your test plan.

### 3. Create a Test Plan

#### For CSV Files

**Quick Start with csv-to-yaml:**

DQ Tester can generate the YAML structure for your CSV file automatically:

```bash
dq_tester -a csv-to-yaml --csv-path examples/datasets/customers.csv
```

This outputs the column definitions which you can copy into your test plan:

```yaml
has_header: true
delimiter: ','
columns:
  - name: Customer Id
    type: VARCHAR
  - name: First Name
    type: VARCHAR
  - name: Email
    type: VARCHAR
  # ... etc
```

**Complete Test Plan:**

Create a test plan (e.g., `file_test_plan.yaml`) by adding the generated output plus source, file_name, and dq_tests:

```yaml
source: csv
file_name: examples/datasets/customers.csv
has_header: true
delimiter: ','
columns:
  - name: Customer Id
    type: VARCHAR
  - name: First Name
    type: VARCHAR
  - name: Email
    type: VARCHAR

dq_tests:
  - dq_test_name: null_values
    column_name: '"Customer Id"'
    threshold:
      type: count
      operator: "=="
      value: 0
  
  - dq_test_name: invalid_email_duckdb
    column_name: '"Email"'
    threshold:
      type: count
      operator: "=="
      value: 0
  
  - dq_test_name: total_records
    threshold:
      type: count
      operator: ">"
      value: 1000
```

**CSV Requirements:**
- `file_name`: Path to the CSV file
- `has_header`: Whether the CSV has a header row
- `delimiter`: Column delimiter (usually `,`)
- `columns`: Column definitions (types are optional)

#### For Databases

Create a test plan (e.g., `db_test_plan.yaml`):

```yaml
source: database
connection_name: sample_db
table_name: sales.salesorderdetail

dq_tests:
  - dq_test_name: null_values
    column_name: salesorderid
    threshold:
      type: count
      operator: "=="
      value: 0
  
  - dq_test_name: duplicate_key
    key_cols: salesorderdetailid
    threshold:
      type: count
      operator: "=="
      value: 0
```

**Database Requirements:**
- `connection_name`: Name from `connections.yaml`
- `table_name`: Fully qualified table name (e.g., `schema.table`)

## CLI Commands

### Run Tests

Execute a test plan against your data:

```bash
dq_tester -a run \
  -c examples/catalog.yaml \
  -t examples/file_test_plan.yaml \
  --connections-path connections.yaml
```

**Required Options:**
- `-a run` or `--action run`: Action to execute
- `-c` or `--catalog-path`: Path to catalog YAML file
- `-t` or `--test-plan-path`: Path to test plan YAML file

**Optional:**
- `--connections-path`: Path to connections YAML file (defaults to searching standard locations)

Validate your catalog and test plan files without running tests:

```bash
dq_tester -a validate \
  -c examples/catalog.yaml \
  -t examples/file_test_plan.yaml
```

**Required Options:**
- `-a validate` or `--action validate`: Action to execute
- `-c` or `--catalog-path`: Path to catalog YAML file
- `-t` or `--test-plan-path`: Path to test plan YAML file

This checks for:
- Valid YAML syntax
- Required fields present
- Proper test configuration
- Parameter matching between catalog and test plan

### Generate CSV YAML Structure

Automatically generate the YAML structure for a CSV file:

```bash
dq_tester -a csv-to-yaml --csv-path examples/datasets/customers.csv
```

**Required Options:**
- `-a csv-to-yaml` or `--action csv-to-yaml`: Action to execute
- `--csv-path`: Path to the CSV file to analyze

This analyzes your CSV file and outputs the column definitions with inferred data types. Copy this output into your test plan to get started quickly.

**Output example:**
```yaml
has_header: true
delimiter: ','
columns:
  - name: Index
    type: BIGINT
  - name: Customer Id
    type: VARCHAR
  - name: Email
    type: VARCHAR
  # ... additional columns
```

### Launch Dashboard

Start the interactive Streamlit dashboard:

```bash
# Use default connections.yaml locations
dq_dashboard

# Specify connections file
dq_dashboard connections.yaml

# Use custom port
dq_dashboard --port 8080 connections.yaml
```

**Options:**
- `connections_file` (positional, optional): Path to connections YAML file
- `--port`: Port number for the dashboard (default: 8501)

**Default connections.yaml locations:**

If no connections file is specified, the dashboard searches in order:
1. `./connections.yaml` (current directory)
2. `~/.dq_tester/connections.yaml` (user home directory)
3. `/etc/dq_tester/connections.yaml` (system-wide)

### Command Reference

```bash
# Show help
dq_tester -h

# Available actions
dq_tester -a {validate,run,csv-to-yaml}

# Full options
dq_tester [-h] 
          [-c CATALOG_PATH] 
          [-t TEST_PLAN_PATH] 
          [--csv-path CSV_PATH]
          [-a {validate,run,csv-to-yaml}]
          [--connections-path CONNECTIONS_PATH]
```

## Built-in DQ Checks

### For CSV Files
- `invalid_records` - Count of records that fail to parse
- `total_records` - Total number of records
- `expected_delimiter` - Validates the delimiter used
- `valid_header` - Validates header structure

### For Databases
- `total_records` - Total number of records in the table

**Note:** Thresholds for built-in checks can be configured in your test plan.

## Thresholds

Tests use thresholds to determine PASS/FAIL status:

### Threshold Types
- **`count`**: Compare absolute count values
- **`pct`**: Compare percentage values (0-100)

### Threshold Operators
- `==`: Equal to
- `!=`: Not equal to
- `<`: Less than
- `<=`: Less than or equal to
- `>`: Greater than
- `>=`: Greater than or equal to

### Example Thresholds

```yaml
# Count-based threshold
threshold:
  type: count
  operator: "=="
  value: 0

# Percentage-based threshold
threshold:
  type: pct
  operator: "<="
  value: 5  # 5% or less
```

## Test Results

Each test produces one of three statuses:

- **PASS**: The test result meets the threshold criteria (threshold comparison returns TRUE)
- **FAIL**: The test result does not meet the threshold criteria
- **ERROR**: The test execution failed (SQL error, connection issue, etc.)

Results are stored in the `results_db` DuckDB database and can be viewed in the dashboard.

## Example Project Structure

```
my-dq-project/
├── connections.yaml
├── catalog.yaml
├── test_plans/
│   ├── customers_test_plan.yaml
│   └── orders_test_plan.yaml
└── results/
    └── test_results.duckdb
```

## Configuration Reference

### Catalog Configuration

```yaml
dq_checks:
  - name: check_name           # Unique name for the check
    type: sql                  # Currently only 'sql' is supported
    sql: |                     # SQL query template
      select count(1)
      from {table_name}
      where {parameter_name} condition
```

### Test Plan Configuration

```yaml
# For CSV
source: csv | database
file_name: path/to/file.csv    # CSV only
has_header: true | false       # CSV only
delimiter: ','                 # CSV only
columns:                       # CSV only
  - name: column_name
    type: data_type            # Optional

# For Database
connection_name: name          # Database only
table_name: schema.table       # Database only

dq_tests:
  - dq_test_name: check_name   # References catalog
    parameter_name: value      # Match parameters in SQL
    threshold:
      type: count | pct
      operator: "==|!=|<|<=|>|>="
      value: number
```

### Connections Configuration

```yaml
connections:
  - name: connection_name
    driver: "PostgreSQL"       # ODBC driver name
    server: "hostname"
    database: "database_name"
    username: "user"
    password: "password"
  
  - name: results_db           # Required for storing results
    driver: "DuckDB"
    database: "./path/to/results.duckdb"
```

## ODBC Driver Setup

### PostgreSQL

**Linux:**
```bash
sudo apt-get install unixodbc unixodbc-dev odbc-postgresql
```

**macOS:**
```bash
brew install unixodbc psqlodbc
```

**Windows:**
Download and install the PostgreSQL ODBC driver from the official website.

### Other Databases

DQ Tester should work with any database that has an ODBC driver. Install the appropriate ODBC driver for your database and configure it in `connections.yaml`.

## Dashboard Features

The Streamlit dashboard provides:

- 📊 **Key Metrics**: Total tests, pass rate, recent failures, columns tested
- 🎯 **Status Distribution**: Visual breakdown of PASS/FAIL/ERROR
- 📈 **Trends Over Time**: Historical test results
- 🔗 **Connection Health**: Test results by connection
- 📋 **Object Analysis**: Test results by tested object
- 🏷️ **Column-Level Health**: Identify problematic columns
- 🔍 **Cascading Filters**: Filter by connection → object → column
- 📥 **CSV Export**: Download filtered results

## Examples

Complete examples are available in the `examples/` directory:
- `catalog.yaml` - Sample DQ check definitions
- `file_test_plan.yaml` - CSV testing example
- `db_test_plan.yaml` - Database testing example
- `connections.yaml` - Connection configuration template

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions, issues, or feature requests, please contact: chad@kodda.io
