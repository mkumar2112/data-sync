from pymongo import MongoClient
from bson import ObjectId

class dql_utility:
    def __init__(self, conn, db_name=None):
        print('----------================', conn, db_name)
        self.conn = conn
        self.db_name = db_name

    def get_db(self):
        if not self.db_name:
            raise ValueError("Database name is not set")
        return self.conn[self.db_name]

    # =============================
    # FILTER / QUERY UTILS
    # =============================
    def where(self, collection_name, filter_dict):
        """
        Return documents matching filter_dict
        """
        db = self.get_db()
        col = db[collection_name]
        return list(col.find(filter_dict))

    def exists(self, collection_name, filter_dict):
        db = self.get_db()
        col = db[collection_name]
        return col.count_documents(filter_dict) > 0

    def distinct(self, collection_name, field):
        db = self.get_db()
        col = db[collection_name]
        return col.distinct(field)

    def count(self, collection_name, filter_dict=None):
        db = self.get_db()
        col = db[collection_name]
        return col.count_documents(filter_dict or {})

    def aggregate(self, collection_name, pipeline):
        db = self.get_db()
        col = db[collection_name]
        return list(col.aggregate(pipeline))

    def full_text_search(self, collection_name, field, keyword):
        db = self.get_db()
        col = db[collection_name]
        return list(col.find({field: {"$regex": keyword, "$options": "i"}}))

    def json_extract(self, collection_name, field, path):
        # MongoDB stores JSON natively, so path can be dot notation
        db = self.get_db()
        col = db[collection_name]
        return list(col.find({}, {field: 1, "_id": 0}))

