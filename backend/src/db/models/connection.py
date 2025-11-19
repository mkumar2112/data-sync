from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean, BigInteger, ForeignKey
from datetime import datetime
from ..base import Base
from sqlalchemy.orm import relationship


class DatabaseConnection(Base):
    __tablename__ = "database_connections"

    id = Column(Integer, primary_key=True, index=True)

    # Basic
    name = Column(String(150), nullable=False)
    db_type = Column(String(50), nullable=False)  # mysql, postgres, mongo, redis, etc.

    # Flexible connection config
    connection_uri = Column(Text, nullable=True)  # For MongoDB, Redis, etc.
    host = Column(String(255), nullable=True)
    port = Column(Integer, nullable=True)
    username = Column(String(150), nullable=True)
    password = Column(String(255), nullable=True)
    database_name = Column(String(150), nullable=True)

    # Ability to store any DB-specific settings  
    config = Column(JSON, nullable=True)  
    # Example: 
    # { "replicaSet": "rs0", "ssl": true, "authSource": "admin", "options": {...} }

    # Metadata about the DB itself
    db_metadata = Column(JSON, nullable=True)
    # Example:
    # { "engine_version": "16.1", "storage": "wiredTiger", "tables": [...], "collections": [...] }

    # Status / Health
    connection_status = Column(String(50), default="unknown")  # connected/failed/unknown
    last_connected_at = Column(DateTime)
    last_error = Column(Text)

    # Sync-related
    auto_sync = Column(Boolean, default=False)
    sync_frequency = Column(String(30), nullable=True)  # hourly/daily/manual
    last_sync_at = Column(DateTime)
    next_sync_at = Column(DateTime)

    # Logs & Usage
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    last_used_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)


class DatabaseHistory(Base):
    __tablename__ = "database_history"

    id = Column(Integer, primary_key=True)
    connection_id = Column(
        Integer,
        ForeignKey("database_connections.id", ondelete="CASCADE"),
        index=True
    )

    sync_id = Column(String(100), nullable=False)  # same sync_id for all related table logs

    # High-level DB metadata snapshot
    db_metadata = Column(JSON, nullable=False)

    # DB size info if available (MySQL/Postgres)
    db_size_mb = Column(Float, nullable=True)

    # Versions / engines / cluster info
    engine = Column(String(100), nullable=True)
    version = Column(String(100), nullable=True)

    # Optional statistics (flexible for NoSQL also)
    stats = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    connection = relationship("DatabaseConnection", backref="db_history")


class DatabaseTable(Base):
    __tablename__ = "database_tables"

    id = Column(Integer, primary_key=True, index=True)

    # Link to parent DB
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=False)

    # Table or collection name
    name = Column(String(255), nullable=False)

    # SQL table / Mongo collection / Graph label / Redis keys pattern
    table_type = Column(String(50), nullable=True)
    # Example: "table", "collection", "view", "materialized_view"

    # SQL only fields (optional)
    schema = Column(String(255), nullable=True)  # public, dbo, etc.
    engine = Column(String(255), nullable=True)  # InnoDB, MyISAM, WiredTiger

    # Row count, size, stats
    row_count = Column(Integer, nullable=True)
    data_size = Column(BigInteger, nullable=True)     # in bytes
    index_size = Column(BigInteger, nullable=True)

    # JSON metadata (flexible)
    options = Column(JSON, nullable=True)
    # Example:
    # { "sharded": true, "clustered": false, "checksum": "abc123" }

    # Last updated automatically
    last_synced_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class DatabaseTableHistory(Base):
    __tablename__ = "database_table_history"

    id = Column(Integer, primary_key=True, index=True)

    # Link to main table
    table_id = Column(Integer, ForeignKey("database_tables.id"), nullable=False)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=False)

    # Snapshot data
    name = Column(String(255), nullable=False)
    table_type = Column(String(50), nullable=True)
    schema = Column(String(255), nullable=True)
    is_schema_changed = Column(Boolean, nullable=True)
    engine = Column(String(255), nullable=True)

    row_count = Column(Integer, nullable=True)
    data_size = Column(BigInteger, nullable=True)
    index_size = Column(BigInteger, nullable=True)

    # JSON metadata snapshot
    options = Column(JSON, nullable=True)

    # TO track syncing
    sync_id = Column(String(100), nullable=True)  
    # Example: unique id for each sync run → "sync_2025_11_19_21_45"

    # When snapshot was created
    snapshot_at = Column(DateTime, default=datetime.utcnow)

class DatabaseColumn(Base):
    __tablename__ = "database_columns"

    id = Column(Integer, primary_key=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id"))
    table_id = Column(Integer, ForeignKey("database_tables.id"))

    table_name = Column(String(200), nullable=False)
    column_name = Column(String(200), nullable=False)

    data_type = Column(String(200))
    is_nullable = Column(Boolean)
    is_primary_key = Column(Boolean)
    is_unique = Column(Boolean)
    default_value = Column(String(500))

    length = Column(Integer)
    precision = Column(Integer)
    scale = Column(Integer)

    foreign_key = Column(JSON)  # optional FK structure

    constraints = Column(JSON)  # 🔥 EXPLAINED ABOVE

    metadata_json = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DatabaseColumnHistory(Base):
    __tablename__ = "column_history"

    id = Column(Integer, primary_key=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id"))
    table_history_id = Column(Integer, ForeignKey("database_table_history.id"))
    column_id = Column(Integer, ForeignKey("database_columns.id"), nullable=True)
    sync_id = Column(String(100), nullable=False)

    table_name = Column(String(200), nullable=False)
    column_name = Column(String(200), nullable=False)

    data_type = Column(String(200))
    is_nullable = Column(Boolean)
    is_primary_key = Column(Boolean)
    is_unique = Column(Boolean)
    default_value = Column(String(500))

    length = Column(Integer)
    precision = Column(Integer)
    scale = Column(Integer)

    foreign_key = Column(JSON)
    constraints = Column(JSON)  # 🔥 SAME STRUCTURE AS Column

    column_metadata = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)



class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # optional
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True)

    event_type = Column(String(100), nullable=False)  
    # examples: "SYNC_STARTED", "SYNC_COMPLETED", "TABLE_ADDED", 
    # "COLUMN_CHANGED", "CONNECTION_UPDATED"

    entity = Column(String(100), nullable=False)
    # "database", "table", "column", "sync-job", "settings"

    entity_id = Column(Integer, nullable=True)  # actual table/column id
    entity_name = Column(String(255), nullable=True)

    description = Column(String(1000), nullable=True)

    before = Column(JSON, nullable=True)  # old state
    after = Column(JSON, nullable=True)   # new state

    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
