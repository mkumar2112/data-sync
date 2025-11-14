from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import all models here
from .models.connection import DatabaseConnection
# from db.models.schema import TableSchema, ColumnSchema
# from db.models.job import Job     # if needed
# from db.models.logs import Logs   # if needed
