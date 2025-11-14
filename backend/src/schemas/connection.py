from pydantic import BaseModel

class DatabaseConnectionBase(BaseModel):
    name: str
    db_type: str
    host: str
    port: int
    username: str
    password: str
    database_name: str

class DatabaseConnectionCreate(DatabaseConnectionBase):
    pass

class DatabaseConnectionOut(BaseModel):
    id: int
    name: str
    db_type: str
    host: str
    port: int
    username: str
    database_name: str

    class Config:
        orm_mode = True
