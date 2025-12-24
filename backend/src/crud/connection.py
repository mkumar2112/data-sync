from sqlalchemy.orm import Session
from backend.src.db.models.connection import DatabaseConnection
from backend.src.schemas.connection import DatabaseConnectionCreate
from pydantic import BaseModel


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
        if isinstance(obj_in, dict):
            data = obj_in
        else:
            data = obj_in.dict()

        obj = self.model(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def get_by_id(self, db: Session, id: int, schema: BaseModel = None):
        obj = db.query(self.model).filter(self.model.id == id).first()
        if not obj:
            return None

        if schema:
            return schema.model_validate(obj).model_dump()   # Convert ORM → Schema

        return obj
    
    def get(self, db: Session, schema: BaseModel = None, **kwargs):
        obj = db.query(self.model).filter_by(**kwargs).first()

        if not obj:
            return None

        if schema:
            return schema.model_validate(obj).model_dump()  # ORM → Pydantic

        return obj

    
    def filter(self, db: Session, page: int = 1, per_page: int = 10, **filters):
        query = db.query(self.model)

        # Apply dynamic filters
        for field, value in filters.items():
            if hasattr(self.model, field) and value is not None:
                query = query.filter(getattr(self.model, field) == value)

        # If per_page = "all", return all records (no pagination)
        if str(per_page).lower() == "all":
            total = query.count()
            items = query.all()
            return {
                "total": total,
                "page": 1,
                "per_page": "all",
                "total_pages": 1,
                "items": items
            }

        # Normal Pagination
        total = query.count()
        total_pages = (total + per_page - 1) // per_page

        items = (
            query
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "items": items
        }


    def get_all(self, db: Session, schema: BaseModel = None):
        """
        Fetch all records. 
        If schema is provided, return a list of Pydantic models.
        """
        records = db.query(self.model).all()
        
        if schema:
            return [schema.from_orm(r) for r in records]
        
        return records

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