import json







class Token:
    def __init__(self, type, value, pos):
        self.type = type
        self.value = value
        self.pos = pos

class Parser:
    def __init__(self):
        pass

    def parse(self, query):
        pass

    

class Executor:
    def __init__(self, catalog_file='catalog.json'):
        self.catalog_file = catalog_file
        self.schema = self.get_schema()

    def get_schema(self):
        with open(self.catalog_file) as f:
            data = json.load(f)
        return data    

    def run(self, query):
        print(self.schema)


query = """ select * from users """

executor = Executor()
parser = Parser()

parser.parse(query)


# executor.run(query)