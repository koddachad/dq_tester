from pydantic import BaseModel, model_validator
from typing import List, Optional,Dict

class DatabaseConnection(BaseModel):
    name: str
    driver: str
    server: Optional[str] = None
    database: str
    username: Optional[str] = None
    password: Optional[str] = None  
    port: Optional[int] = None
    additional_params: Optional[Dict[str, str]] = None

class Connections(BaseModel):
    connections: List[DatabaseConnection]

    @model_validator(mode="after")
    def check_unique_names(self):
        names = [c.name for c in self.connections]
        duplicates = {name for name in names if names.count(name) > 1}
        if duplicates:
            raise ValueError(f"Duplicate connection names not allowed: {duplicates}")
        return self    

    def get_connection(self, name):
        for c in self.connections:
            if c.name==name:
                return c
        return None

