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

types = {'int': int, 'char': str}


one_char_operators = {'=': Tokentype.EQ, '<': Tokentype.LT, '>': Tokentype.GT}
two_char_operators = {'!=': Tokentype.NEQ,'<>': Tokentype.NEQ, '<=': Tokentype.LTE, '>=': Tokentype.GTE}

OPERATORS = (list(one_char_operators.values()) + list(two_char_operators.values()))

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
    from_: Table
    where: Comparision | AND | OR = None

@dataclass
class Column:
    col: str
    table: str = None
    index: int = None
    type: str = None


@dataclass
class Table:
    table: str

@dataclass
class Literal:
    val: int | str

@dataclass
class Star:
    pass


@dataclass
class Comparision:
    left: Literal | Column
    op: Tokentype
    right: Literal | Column

@dataclass
class AND:
    left: Comparision | AND | OR
    right: Comparision | AND | OR

@dataclass
class OR:
    left: Comparision | AND | OR
    right: Comparision | AND | OR


class Parser:
    def __init__(self):
        self.tokens = []
        self.position = 0
    
    def current(self):
        assert self.tokens is not None
        return self.tokens[self.position]

    def advance(self):
        assert self.tokens is not None
        if self.position >= len(self.tokens) - 1: return self.tokens[self.position] # at eof
        self.position += 1
        return self.tokens[self.position-1]

    def peek(self):
        assert self.tokens is not None
        if self.position >= len(self.tokens) - 1: return self.tokens[self.position] #eof
        return self.tokens[self.position+1]

    def expect(self, type):
        if self.current().type != type:
            raise ValueError(f"Expected {type}, got {self.current()} in position {self.current().pos}")

    def parse(self, tokens):
        self.tokens = tokens
        self.position = 0

        parsed_query = self.parse_query()

        return parsed_query
    


    def parse_query(self):
        self.expect(Tokentype.SELECT)
        token = self.advance()

        columns = self.parse_columns()   


        self.expect(Tokentype.FROM)
        token = self.advance()
        tables = self.parse_from()
        
        token = self.current()
        
        if token.type == Tokentype.WHERE:
            token = self.advance()
            filters = self.parse_where()
        else: filters = None 

        self.expect(Tokentype.EOF)

        return Select(columns, tables,  filters)

    
    def parse_columns(self):
        columns = []
        while True:
            next_token = self.current()
            if next_token.type == Tokentype.IDENTIFIER:
                token = self.advance()
                columns.append(Column(token.value)) 
            elif next_token.type == Tokentype.STAR:
                token = self.advance()
                columns.append(Star()) 
            else: self.expect(Tokentype.IDENTIFIER)
            
            next_token = self.current()
            if next_token.type == Tokentype.COMMA: 
                token = self.advance()
                continue
            else: break
        return columns


    def parse_from(self):
        self.expect(Tokentype.IDENTIFIER)
        token = self.advance()
        return Table(token.value)


    def parse_where(self):
        comparision = self.parse_or()
        return comparision

    def parse_or(self):
        comparision = self.parse_and()
        while self.current().type == Tokentype.OR:
            self.advance()
            comparision_right = self.parse_and()
            comparision = OR(comparision, comparision_right)
        return comparision


    def parse_and(self):
        comparision = self.parse_condition()
        while self.current().type == Tokentype.AND:

            self.advance()
            comparision_right = self.parse_condition()
            comparision = AND(comparision, comparision_right)

        return comparision

    def parse_operand(self):
        next_token = self.current()

        if next_token.type == Tokentype.IDENTIFIER:
            token = self.advance()
            val = Column(token.value)
        elif next_token.type in (Tokentype.STRING, Tokentype.INT):
            token = self.advance()
            val = Literal(token.value)
        else: self.expect('IDENTIFIER, INT or STR')
        
        return val

            
    def parse_condition(self):
        left = self.parse_operand()
    
        next_token = self.current()
        if next_token.type not in OPERATORS: self.expect('OPERATOR')
        op = self.advance().type
        right = self.parse_operand()
        
        return Comparision(left, op, right)


class Binder:
    def __init__(self, catalog_file='catalog.json'):
        self.catalog_file = catalog_file
        self.schema = self.get_schema()
        self.parsed_tokens = None
        self.table_list = []

    def get_schema(self):
        with open(self.catalog_file) as f:
            data = json.load(f)
        return data

    def bind(self, parsed_tokens):
        self.parsed_tokens = parsed_tokens

        self.check_tables()

        self.check_columns()

        self.check_where()

        return self.parsed_tokens

    def check_where(self):
        tree = self.parsed_tokens.where


        def recursive_check(el):
            if isinstance(el, (AND, OR)):
                el.left = recursive_check(el.left)
                el.right = recursive_check(el.right)

            else:
                l, r, op = el.left, el.right, el.op
                if isinstance(l, Column): l = self.check_column(l)[0]
                if isinstance(r, Column): r = self.check_column(r)[0]

                # w have 3 comparision: literal literal, column column and literal column (and column literal but this doesnt matter since its the same)

                if isinstance(l, Literal) and isinstance(r, Literal):
                    if not type(l.val) == type(r.val): raise ValueError(f'Cant compare types {type(l.val)} and {type(r.val)}')
                elif isinstance(l, Column) and isinstance(r, Column):
                    if not l.type == r.type: raise ValueError(f'Cant compare types {l.type} and {r.type}')
                else:
                    if isinstance(l, Column):
                        if not types[l.type] == type(r.val): raise ValueError(f'Cant compare types {types[l.type]} and {type(r.val)}')
                    else: 
                        if not type(l.val) == types[r.type]: raise ValueError(f'Cant compare types {type(l.val)} and {types[r.type]}')
                    
                return Comparision(l, op, r)
            
            return el

        if tree:
            self.parsed_tokens.where = recursive_check(tree)


    def check_tables(self):
        # for now query has only singel table
        query_tables = [self.parsed_tokens.from_.table]

        self.table_list = []
        for table in query_tables:
            if table not in self.schema['tables']: raise ValueError(f"Table {table} not in the schema")
            else: self.table_list.append((table, self.schema['tables'][table]))


    def check_column(self, col):

        if isinstance(col, Star):
            columns = []
            for name, table in self.table_list:
                for table_ind, table_col in enumerate(table['columns']): columns.append(Column(table_col['name'], name, table_ind, table_col['type']))
            return columns 
        else:
            matched = []
            if col.table:
                raise NotImplementedError
            else:
                for table_name, table in self.table_list:
                    for table_ind, table_col in enumerate(table['columns']):
                        if table_col['name'] == col.col:
                            matched.append([table_col['name'], table_name, table_ind, table_col['type']])
                            break # only single col with same name in singel table

            if len(matched) == 0: raise ValueError(f"Column {col} not found")
            elif len(matched) > 1: raise ValueError(f"Ambiguous column name {col}")
            else:
                col_name, table_name, table_ind, col_type = matched[0]
                return [Column(col_name, table_name, table_ind, col_type)]

    def check_columns(self):
        new_col_list = []
        for col in self.parsed_tokens.columns: new_col_list += self.check_column(col)
        self.parsed_tokens.columns = new_col_list

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


query = """ SELECT id FROM users where id != 21"""

executor = Executor()
tokenizer = Tokenizer()
parser = Parser()
binder = Binder()

tokens = tokenizer.tokenize(query)
# print(tokens)
parsed_tokens = parser.parse(tokens)

print(parsed_tokens)

query_tree = binder.bind(parsed_tokens)
print(query_tree)
# print(query_tree)
executor.run(query_tree)