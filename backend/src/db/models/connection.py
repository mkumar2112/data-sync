from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from ..base import Base
from sqlalchemy.orm import relationship

class DatabaseConnection(Base):
    __tablename__ = "database_connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    db_type = Column(String(20), nullable=False)  # mysql or postgres
    host = Column(String(255), nullable=False)
    port = Column(Integer, default=3306)
    username = Column(String(100), nullable=False)
    password = Column(String(255), nullable=False)
    database_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # tables = relationship("TableSchema", back_populates="db", cascade="all, delete")
