import string
from pydantic import BaseModel, validator, model_validator, ValidationError
from typing import List, Optional, Literal


class DqCheck(BaseModel):
    name: str
    type: Literal["sql","system","schema"]
    sql: Optional[str] = None
    sql_params: Optional[List[str]] = None

    @model_validator(mode="after")
    def set_sql_params(self):
        # SET sql_params
        if self.type=='sql':
            formatter=string.Formatter()
            sp=[]
            for i in formatter.parse(self.sql):
                if i[1] is not None and i[1] not in sp:
                    sp.append(i[1])
            self.sql_params=sp
        return self

class Catalog(BaseModel):
    dq_checks: List[DqCheck]

    @model_validator(mode="after")
    def check_unique_names(self):
        names = [dq.name for dq in self.dq_checks]
        duplicates = {name for name in names if names.count(name) > 1}
        if duplicates:
            raise ValueError(f"Duplicate dq_check names not allowed: {duplicates}")
        return self

    def get_dq_check(self, name):
        for c in self.dq_checks:
            if c.name==name:
                return c
        return None














