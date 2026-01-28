





class LoadService:
    def __init__(self, request, db, dml_opr, **kwargs):
        self.request =  request
        self.db = db
        self.dml_opr = dml_opr

    def run(self, data):

        flag , data = self.dml_opr.load_data(table_name=table_name)
        
        return {"rows_loaded": len(data)}


