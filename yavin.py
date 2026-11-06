import json
from enum import Enum, auto




class Tokentype(Enum):
    STRING = auto()     # auto() picks a value for you (1, 2, 3...)
    IDENTIFIER = auto()     # auto() picks a value for you (1, 2, 3...)
    INT = auto()     # auto() picks a value for you (1, 2, 3...)

    # operators
    EQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()
        
    # symbols
    STAR = auto()     # auto() picks a value for you (1, 2, 3...)
    COMMA = auto()

    
    # keywords
    SELECT = auto()     # auto() picks a value for you (1, 2, 3...)
    FROM = auto()     # auto() picks a value for you (1, 2, 3...)
    WHERE = auto()     # auto() picks a value for you (1, 2, 3...)
    AND = auto()
    OR = auto()
        
    
keywords = {'SELECT': Tokentype.SELECT, 'FROM': Tokentype.FROM, 'WHERE': Tokentype.WHERE, 'AND': Tokentype.AND, 'OR': Tokentype.OR}

symbols = {'*': Tokentype.STAR, ',': Tokentype.COMMA}


one_char_operators = {'=': Tokentype.EQ, '<': Tokentype.LT, '>': Tokentype.GT}
two_char_operators = {'!=': Tokentype.NEQ,'<>': Tokentype.NEQ, '<=': Tokentype.LTE, '>=': Tokentype.GTE}

class Token:
    def __init__(self, type, value, pos):
        self.type = type
        self.value = value
        self.pos = pos

    def __repr__(self):
        return f"Token({self.value}, {self.type})"

    def __str__(self):
        return f"Token({self.value}, {self.type})"


class Parser:
    def __init__(self):
        self.query = None
        self.tokens = []
        self.position = 0

    def parse(self, query):
        tokens = self.tokenize(query)
        print(tokens)

    def add(self, type, value, position):
        self.tokens.append(Token(type, value, position))

    def current(self):
        assert self.query is not None
        if self.position >= len(self.query) - 1: return ""
        return self.query[self.position]

    def advance(self):
        assert self.query is not None
        if self.position >= len(self.query) - 1: return ""
        self.position += 1
        return self.query[self.position]

    def peek(self):
        assert self.query is not None
        if self.position >= len(self.query) - 1: return ""
        return self.query[self.position+1]

    def tokenize(self, query):
        self.query = query
        self.tokens = []
        self.position = 0

        char = self.current()
        while True:
            if char.isspace(): pass # skip spaces

            elif char.isalpha() or char == "_": # start of a word
                string = char
                start_pos = self.position
                while True:
                    next_char = self.peek()
                    if not (next_char.isalpha() or next_char == "_" or next_char.isdigit()):
                        if string.upper() in keywords.keys(): type = keywords[string.upper()]
                        else: type = Tokentype.IDENTIFIER
                        self.add(type, string, start_pos)
                        break
                    char = self.advance()
                    string += char


            elif char in symbols: self.add(symbols[char], char, self.position) 

            elif char in one_char_operators:
                next_char = self.peek()
                start_pos = self.position
                if next_char in one_char_operators:
                   if char + next_char in two_char_operators:
                        next_char = self.advance()
                        self.add(two_char_operators[char + next_char], char + next_char, start_pos)
                   else: raise ValueError("Unknown operator", char + next_char)
                else: self.add(one_char_operators[char], char, start_pos) 
        
                
            elif char in ('\'', '\"'): # start of a string
                string = ""
                start_pos = self.position + 1
                while True:
                    next_char = self.advance()
                    if next_char in ('\'', '\"') or not next_char: 
                        self.add(Tokentype.STRING, string, start_pos)
                        break
                    string += next_char

            elif char.isdigit(): # start of a number
                number = char
                start_pos = self.position
                while True:
                    next_char = self.peek()
                    if not (next_char.isdigit()):
                        try: number = int(number)
                        except ValueError: raise ValueError(number)
                        self.add(Tokentype.INT, number, start_pos)
                        break
                    next_char = self.advance()
                    number += next_char

            else: # unknown
                raise ValueError("Unknown value: ", char)

            char = self.advance()
            if char == '': break
        return self.tokens


    

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


query = """ SELECT * FROM t where a < 21 and c = "lsdkf" """

executor = Executor()
parser = Parser()

parser.parse(query)

# executor.run(query)