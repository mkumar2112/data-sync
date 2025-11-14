from sqlalchemy.orm import Session
from backend.src.db.models.connection import DatabaseConnection
from backend.src.schemas.connection import DatabaseConnectionCreate

def create_connection(db: Session, data: DatabaseConnectionCreate):
    db_conn = DatabaseConnection(**data.dict())
    db.add(db_conn)
    db.commit()
    db.refresh(db_conn)
    return db_conn


def get_all_connections(db: Session):
    return db.query(DatabaseConnection).all()

class CRUDBase:
    def __init__(self, model):
        self.model = model

    def create(self, db: Session, obj_in):
        obj = self.model(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def get(self, db: Session, id: int):
        return db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, db: Session):
        return db.query(self.model).all()

    def update(self, db: Session, db_obj, obj_in):
        for key, value in obj_in.dict().items():
            setattr(db_obj, key, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int):
        obj = db.query(self.model).filter(self.model.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj


# connection_crud = CRUDBase(DatabaseConnection)