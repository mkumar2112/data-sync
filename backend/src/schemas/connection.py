from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime


class DatabaseConnectionBase(BaseModel):
    name: str
    db_type: str
    host: Optional[str]
    port: Optional[int]
    username: Optional[str]
    password: Optional[str]
    database_name: Optional[str]
    connection_uri: Optional[str]
    config: Optional[Dict[str, Any]]
    db_metadata: Optional[Dict[str, Any]]
    auto_sync: Optional[bool] = False
    sync_frequency: Optional[str]


class DatabaseConnectionCreate(DatabaseConnectionBase):
    pass


class DatabaseConnectionUpdate(BaseModel):
    name: Optional[str]
    host: Optional[str]
    port: Optional[int]
    username: Optional[str]
    password: Optional[str]
    database_name: Optional[str]
    connection_uri: Optional[str]
    config: Optional[Dict[str, Any]]
    auto_sync: Optional[bool]
    sync_frequency: Optional[str]


class DatabaseConnectionOut(BaseModel):
    id: int
    name: str
    db_type: str
    host: Optional[str]
    port: Optional[int]
    username: Optional[str]
    database_name: Optional[str]
    connection_status: Optional[str]
    last_connected_at: Optional[datetime]

    class Config:
        orm_mode = True



class DatabaseHistoryBase(BaseModel):
    connection_id: int
    sync_id: str
    db_metadata: Dict[str, Any]
    db_size_mb: Optional[float]
    engine: Optional[str]
    version: Optional[str]
    stats: Optional[Dict[str, Any]]


class DatabaseHistoryCreate(DatabaseHistoryBase):
    pass


class DatabaseHistoryOut(DatabaseHistoryBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class DatabaseTableBase(BaseModel):
    connection_id: int
    name: str
    table_type: Optional[str]
    schema: Optional[str]
    engine: Optional[str]
    row_count: Optional[int]
    data_size: Optional[int]
    index_size: Optional[int]
    options: Optional[Dict[str, Any]]


class DatabaseTableCreate(DatabaseTableBase):
    pass


class DatabaseTableOut(DatabaseTableBase):
    id: int
    last_synced_at: Optional[datetime]
    created_at: datetime

    class Config:
        orm_mode = True


class DatabaseTableHistoryBase(BaseModel):
    table_id: int
    connection_id: int
    name: str
    table_type: Optional[str]
    schema: Optional[str]
    is_schema_changed: Optional[bool]
    engine: Optional[str]
    row_count: Optional[int]
    data_size: Optional[int]
    index_size: Optional[int]
    options: Optional[Dict[str, Any]]
    sync_id: Optional[str]


class DatabaseTableHistoryCreate(DatabaseTableHistoryBase):
    pass


class DatabaseTableHistoryOut(DatabaseTableHistoryBase):
    id: int
    snapshot_at: datetime

    class Config:
        orm_mode = True


class DatabaseColumnBase(BaseModel):
    connection_id: int
    table_id: int
    table_name: str
    column_name: str

    data_type: Optional[str]
    is_nullable: Optional[bool]
    is_primary_key: Optional[bool]
    is_unique: Optional[bool]
    default_value: Optional[str]

    length: Optional[int]
    precision: Optional[int]
    scale: Optional[int]

    foreign_key: Optional[Dict[str, Any]]
    constraints: Optional[Dict[str, Any]]
    metadata_json: Dict[str, Any]


class DatabaseColumnCreate(DatabaseColumnBase):
    pass


class DatabaseColumnOut(DatabaseColumnBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True



class DatabaseColumnHistoryBase(BaseModel):
    connection_id: int
    table_history_id: int
    column_id: Optional[int]
    sync_id: str

    table_name: str
    column_name: str

    data_type: Optional[str]
    is_nullable: Optional[bool]
    is_primary_key: Optional[bool]
    is_unique: Optional[bool]
    default_value: Optional[str]

    length: Optional[int]
    precision: Optional[int]
    scale: Optional[int]

    foreign_key: Optional[Dict[str, Any]]
    constraints: Optional[Dict[str, Any]]
    column_metadata: Dict[str, Any]


class DatabaseColumnHistoryCreate(DatabaseColumnHistoryBase):
    pass


class DatabaseColumnHistoryOut(DatabaseColumnHistoryBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True



class AuditLogBase(BaseModel):
    connection_id: Optional[int]
    event_type: str
    entity: str
    entity_id: Optional[int]
    entity_name: Optional[str]
    description: Optional[str]
    before: Optional[Dict[str, Any]]
    after: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogOut(AuditLogBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
