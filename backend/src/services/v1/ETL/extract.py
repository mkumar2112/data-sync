from ....core.status import DBStatus, api_response


class ExtractService:

    def __init__(self, dql_opr):
        self.dql_opr = dql_opr

    async def get_table_data(self, table_name):
        flag, data = self.dql_opr.get_all_data(table_name)
        if not flag:
            return None, api_response(400, message = data)
        return True, data
    
    async def get_all_table_data(self, table_list):
        table_data = {}
        for table in table_list:
            flag, data = self.dql_opr.get_all_data(table.name)
            if not flag:
                return None, api_response(400, message = data)
            table_data[table.name] = data
        return True, table_data
    

