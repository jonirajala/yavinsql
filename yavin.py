from __future__ import annotations 
import json
from enum import Enum, auto
from dataclasses import dataclass



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

    EOF = auto()
        
    
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


class Tokenizer:
    def __init__(self):
        self.query = None
        self.tokens = []
        self.position = 0

    def add(self, type, value, position):
        self.tokens.append(Token(type, value, position))

    def current(self):
        assert self.query is not None
        if self.position >= len(self.query): return ""
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

        if not query:
            self.add(Tokentype.EOF, 'EOF', self.position)
            return self.tokens # handling empty query

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


            elif char in symbols: self.add(symbols[char], char, self.position) # symbols

            elif char in one_char_operators or char == '!': # Operators
                next_char = self.peek()
                start_pos = self.position
                if char + next_char in two_char_operators:
                    next_char = self.advance()
                    self.add(two_char_operators[char + next_char], char + next_char, start_pos)
                elif char in one_char_operators:
                    self.add(one_char_operators[char], char, start_pos)
                else: raise ValueError("Unknown operator", char + next_char)
        
                
            elif char in ('\'', '\"'): # start of a string
                string = ""
                start_pos = self.position
                start_char = char
                while True:
                    next_char = self.advance()
                    if next_char == start_char: 
                        self.add(Tokentype.STRING, string, start_pos)
                        break
                    elif not next_char:
                        raise ValueError('String not ended')
                    string += next_char


            elif char.isdigit(): # start of a number
                number = char
                start_pos = self.position
                while True:
                    next_char = self.peek()
                    if not (next_char.isdigit()):
                        if next_char.isalpha(): raise ValueError("Invalid number: ", number + next_char)
                        number = int(number)
                        self.add(Tokentype.INT, number, start_pos)
                        break
                    next_char = self.advance()
                    number += next_char

            else: # unknown
                raise ValueError("Unknown value: ", char)

            char = self.advance()
            if char == '': break
        self.add(Tokentype.EOF, 'EOF', self.position+1)
        return self.tokens



"""
What it's for. The tokenizer gave you a flat list of tokens: words, but no sentences. The parser answers two questions:
1. Is this a valid query? Are the tokens in an order the grammar allows?
2. What does it mean, structurally? Which tokens are the columns, which is the table, which form the conditions?

Input: the list of tokens. Output: the AST, a structured object describing the query. For example, SELECT name, age FROM users WHERE age > 18 becomes something like:
- a select query with
  - columns: name, age
  - table: users
  - where: a comparison of column age, operator > and literal 18

The executor never sees tokens or text, only this structure.

What it should do
- Follow the grammar: SELECT, then a column list, then FROM, then a table name, then optionally WHERE and a condition
- Reject anything else with a clear error, using the token positions: "expected FROM at position 12, got IDENTIFIER". The <=< and =< cases end up here.
- Make sure all tokens are used: after a complete query, the next token must be EOF. Otherwise SELECT a FROM t garbage would be accepted.
- Build the AST nodes as it goes

What it should not do
- Look at the catalog. Whether users or age exists is the binder's job.
- Read data or evaluate conditions. That's the executor.
- Deal with characters or spaces. That was the tokenizer's job.

How (recursive descent)
- Each grammar rule becomes one method: parse a query, parse a column list, parse a condition, parse a comparison
- Each method consumes the tokens for its rule using peek, advance and expect, and returns an AST node
- Rules call each other: the query rule calls the column list rule, and later the condition rule

A good first step: write your grammar in words or BNF and decide which AST classes you need. Then each method is mostly a direct translation of a grammar rule.

select name, age
from users
where age > 100

it looks like:

Query {
  columns: [ {table: null, col: "name"}, {table: null, col: "age"} ],
  from: Table { name: "users", alias: null },
  where: { left: {table: null, col: "age"}, op: ">", right: 100 }
}



SELECT u.name, o.total
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE o.total > 100

it looks like:

Query {
  columns: [ {table: "u", col: "name"}, {table: "o", col: "total"} ],
  from: Join {
    type: "inner",
    left:  Table { name: "users",  alias: "u" },
    right: Table { name: "orders", alias: "o" },
    on: { left: {table: "u", col: "id"}, op: "=", right: {table: "o", col: "user_id"} }
  },
  where: { left: {table: "o", col: "total"}, op: ">", right: 100 }
}

"""

@dataclass
class Select:
    columns: list
    from_: str
    where: list

@dataclass
class Column:
    col: str
    table: str = None

@dataclass
class Table:
    table: str

@dataclass
class Literal:
    val: int | str

@dataclass
class Comparision:
    left: Literal | Column
    op: Tokentype
    right: Literal | Column

@dataclass
class AND:
    left: Comparision | AND | OR
    right: Comparision | AND | OR

class OR:
    left: Comparision | AND | OR
    right: Comparision | AND | OR


class Parser:
    def __init__(self):
        self.tokens = []
        self.position = 0
        self.parsed_query = {'columns': [], 'from': [], 'where': []}

    
    def current(self):
        assert self.tokens is not None
        return self.tokens[self.position]

    def advance(self):
        assert self.tokens is not None
        if self.position >= len(self.tokens) - 1: return ""
        self.position += 1
        return self.tokens[self.position]

    def peek(self):
        assert self.tokens is not None
        if self.position >= len(self.tokens) - 1: return ""
        return self.tokens[self.position+1]


    def parse(self, tokens):
        self.tokens = tokens
        self.position = 0
        self.parsed_query = {'columns': [], 'from': [], 'where': []}

        self.parse_query()
        return self.parsed_query



    def parse_query(self):
        token = self.current()
        if token.type != Tokentype.SELECT: raise ValueError(f"Expected SELECT, got {token} in position {self.position}")
        token = self.advance()

        self.parse_columns()

        token = self.current()
        if token.type != Tokentype.FROM: raise ValueError(f"Expected FROM, got {token} in position {self.position}")
        self.parse_from()
        
        
        token = self.advance()
        
        if token.type == Tokentype.WHERE: self.parse_where()
        elif token.type == Tokentype.EOF: return
        else: raise ValueError(f"Expected EOF, got {token} in position {self.position}")

    
    def parse_columns(self):
        while True:
            token = self.current()
            if token.type  not in (Tokentype.IDENTIFIER, Tokentype.STAR) : raise ValueError(f"Expected IDENTIFIER, got {token} in position {self.position}")
            self.parsed_query['columns'].append(Column(token.value))

            token = self.advance()

            if token.type == Tokentype.COMMA: token = self.advance()
            else: return


    def parse_from(self):
        token = self.advance()
        if token.type != Tokentype.IDENTIFIER: raise ValueError(f"Expected IDENTIFIER, got {token} in position {self.position}")
        self.parsed_query['from'] = token.value

    def parse_where(self):
        while True:
            comparision = self.parse_condition()
            token = self.advance()

            if token.type == Tokentype.AND:
                comparision_right = self.parse_condition()
                comp = AND(comparision, comparision_right)
            elif token.type == Tokentype.OR:
                comparision_right = self.parse_condition()
                comp = OR(comparision, comparision_right)

            else: return


            
    def parse_condition(self):
        left_token = self.advance()

        if left_token.type == Tokentype.IDENTIFIER: left = Column(left_token.value)
        elif left_token.type in (Tokentype.STRING, Tokentype.INT): left = Literal(left_token.value)
        else: raise ValueError(f"Expected IDENTIFIER, INT or STR, got {left_token} in position {self.position}")

        


        op_token = self.advance()

        if op_token.type not in (list(one_char_operators.keys()) + list(two_char_operators.keys())): raise ValueError(f"Expected operator, got {left_token} in position {self.position}")

        right_token = self.advance()
        if right_token.type == Tokentype.IDENTIFIER: left = Column(right_token.value)
        elif right_token.type in (Tokentype.STRING, Tokentype.INT): left = Literal(right_token.value)
        else: raise ValueError(f"Expected IDENTIFIER, INT or STR, got {right_token} in position {self.position}")
        
        return Comparision(right_token.value, op_token, right_token.value)

    


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


query = """ SELECT name, id FROM t where a != 21 and c = "lsdkf" """

executor = Executor()
tokenizer = Tokenizer()

tokens = tokenizer.tokenize(query)

parser = Parser()
parsed_tokens = parser.parse(tokens)

print(parsed_tokens)
# executor.run(query)