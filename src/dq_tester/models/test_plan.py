from pydantic import BaseModel,  model_validator,  ConfigDict, constr
from typing import List, Optional, Literal

class Threshold(BaseModel):
    type: Literal["count","pct"]
    operator: Literal["<","<=","==",">=",">"]
    value: int

class DqTest(BaseModel):
    dq_test_name: str
    threshold: Threshold
    model_config = ConfigDict(extra="allow")

#TODO Validate types using source
class Column(BaseModel):
    name: str
    type: Optional[Literal['BOOLEAN', 'BIGINT', 'DOUBLE', 'TIME', 'DATE', 'TIMESTAMP', 'VARCHAR']] = None

class TestPlan(BaseModel):
    source: Literal["csv", "database"]
    dq_tests: List[DqTest]
    file_name: Optional[str] = None
    has_header: Optional[bool] = None
    delimiter: Optional[constr(min_length=1, max_length=1)] = None
    columns: Optional[List[Column]] = None
    connection_name: Optional[str] = None
    table_name: Optional[str] = None

    @model_validator(mode="after")
    def check_required_fields(self):

        required_fields = {
            'csv': ['file_name', 'has_header', 'delimiter', 'columns'],
            'database': ['connection_name', 'table_name']
        }

        for field in required_fields.get(self.source, []):
            if getattr(self, field, None) is None:
                raise ValueError(f"{field} is required when source = '{self.source}'")

        return self

    @model_validator(mode="after")
    def check_unique_names(self):

        if self.columns:
            names = [c.name for c in self.columns]
            duplicates = {name for name in names if names.count(name) > 1}
            if duplicates:
                raise ValueError(f"Duplicate column names not allowed: {duplicates}")
        return self

    def columns_as_dict(self):
        return {col.name: (col.type or 'VARCHAR') for col in self.columns}

    def get_dq_test(self, dq_test_name):
        for t in self.dq_tests:
            if t.dq_test_name==dq_test_name:
                return t
        return None















