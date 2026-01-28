from sqlalchemy.orm import declarative_base
from datetime import datetime, date, time
from decimal import Decimal

Base = declarative_base()

class MasterBase:
    __abstract__ = True  # prevents table creation

    def to_dict(self):
        result = {}
        for c in self.__table__.columns:
            value = getattr(self, c.name)

            if isinstance(value, (datetime, date, time)):
                result[c.name] = value.isoformat()

            elif isinstance(value, Decimal):
                result[c.name] = float(value)

            else:
                result[c.name] = value

        return result
