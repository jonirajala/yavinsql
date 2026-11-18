from __future__ import annotations 
import json
from enum import Enum, auto
from dataclasses import dataclass
import struct
import operator
from operator import itemgetter

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
    LPAREN = auto()
    RPAREN = auto()
    
    # keywords
    SELECT = auto()     # auto() picks a value for you (1, 2, 3...)
    FROM = auto()     # auto() picks a value for you (1, 2, 3...)
    WHERE = auto()     # auto() picks a value for you (1, 2, 3...)
    AND = auto()
    OR = auto()
    INSERT = auto()
    INTO = auto()
    VALUES = auto()


    EOF = auto()
        
    
keywords = {'SELECT': Tokentype.SELECT, 'FROM': Tokentype.FROM, 'WHERE': Tokentype.WHERE, 'AND': Tokentype.AND, 'OR': Tokentype.OR, 'INSERT': Tokentype.INSERT, 'INTO': Tokentype.INTO, 'VALUES': Tokentype.VALUES}
symbols = {'*': Tokentype.STAR, ',': Tokentype.COMMA, '(': Tokentype.LPAREN, ')': Tokentype.RPAREN}

types = {'int': int, 'char': str}


one_char_operators = {'=': Tokentype.EQ, '<': Tokentype.LT, '>': Tokentype.GT}
two_char_operators = {'!=': Tokentype.NEQ,'<>': Tokentype.NEQ, '<=': Tokentype.LTE, '>=': Tokentype.GTE}

OPERATORS = (list(one_char_operators.values()) + list(two_char_operators.values()))

OPERATOR_DICT = {Tokentype.EQ: operator.eq, Tokentype.LT: operator.lt, Tokentype.GT: operator.gt, Tokentype.NEQ: operator.ne, Tokentype.LTE: operator.le, Tokentype.GTE: operator.ge }

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
class Insert:
    to: Table
    values: list


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

        if self.position == 0: return self.tokens[self.position]
        return self.tokens[self.position+1]

    def expect(self, type):
        if self.current().type != type:
            raise ValueError(f"Expected {type}, got {self.current()} in position {self.current().pos}")

    def parse(self, tokens):
        self.tokens = tokens
        self.position = 0

        first_token = self.peek()

        if first_token.type  == Tokentype.SELECT:
            parsed_query = self.parse_select()
        elif first_token.type  == Tokentype.INSERT:
            parsed_query = self.parse_insert()
        

        return parsed_query
    


    def parse_select(self):
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


    def parse_insert(self):
        """ Possible extensions, later
- A column list: INSERT INTO users (id, name) VALUES (...), where the missing columns get defaults
- Several rows at once: VALUES (...), (...), which is just a comma loop around parse_values
"""
        self.expect(Tokentype.INSERT)
        token = self.advance()

        self.expect(Tokentype.INTO)
        token = self.advance()

        self.expect(Tokentype.IDENTIFIER)
        table = Table(self.advance().value)

        self.expect(Tokentype.VALUES)
        token = self.advance()

        values = self.parse_values()
        
        self.expect(Tokentype.EOF)

        return Insert(table, values)


    def parse_values(self):
        values = []
        self.expect(Tokentype.LPAREN)
        token = self.advance()

        while True:
            next_token = self.current()
            if next_token.type in (Tokentype.INT, Tokentype.STRING):
                token = self.advance()
                values.append(Literal(token.value))
            else:
                self.expect(Tokentype.INT) ## needs fix when we implement multi error 

            next_token = self.current()
            if next_token.type == Tokentype.COMMA: 
                token = self.advance()
                continue
            elif next_token.type == Tokentype.RPAREN:
                token = self.advance()
                break
            else: self.expect(Tokentype.RPAREN)

        return values

    
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

        if isinstance(parsed_tokens, Select):
            self.bind_select()
        elif isinstance(parsed_tokens, Insert):
            self.bind_insert()
        else:
            raise NotImplementedError()

        return self.parsed_tokens


    def bind_insert(self):
        self.check_tables_insert()

        self.check_values()

        return self.parsed_tokens

    def bind_select(self):
        self.check_tables_select()

        self.check_columns()

        self.check_where()

        return self.parsed_tokens

    def check_values(self):
        # number of values equals the number of cols
        insert_vals = self.parsed_tokens.values
        schema_cols = self.schema['tables'][self.parsed_tokens.to.table]['columns']


        # number of values equals the number of cols
        if len(insert_vals) != len(schema_cols): raise ValueError(f"Number of values {len(insert_vals)} doesnt match the number of column in the table {len(schema_cols)}")

        
        for insert_val, schema_col in zip(insert_vals, schema_cols):
            # each values type matches its column type
            if type(insert_val.val) != types[schema_col['type']]: raise ValueError(f"Cant insert type {type(insert_val.val)} to a type {types[schema_col['type']]}") 

            # strings fit the column char size
            if schema_col['type'] == 'char':
                char_len = len(insert_val.val.encode())
                if char_len > schema_col['size']: raise ValueError(f"Value {insert_val} is too long for char column")


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

    def check_tables_insert(self):
        # for now query has only singel table
        insert_table = self.parsed_tokens.to.table

        self.table_list = []
        if insert_table not in self.schema['tables']: raise ValueError(f"Table {insert_table} not in the schema")
        else: self.table_list.append((insert_table, self.schema['tables'][insert_table]))
 

    def check_tables_select(self):
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


STRUCT_CODES = {'int': "i", 'char': '8s'}

class Executor:
    def __init__(self, catalog_file='catalog.json'):
        self.catalog_file = catalog_file
        self.schema = self.get_schema()

        self.struct_info = {}
        self.tables = {}

    def get_schema(self):
        with open(self.catalog_file) as f:
            data = json.load(f)
        return data

    def create_struct_strings(self):
        for table_name, table_doc in self.tables.items():
            cols = table_doc['columns']
            codes = "<"
            size = 0
            for col in cols:
                size += col['size']
                codes += STRUCT_CODES[col['type']]

            self.struct_info[table_name] = (codes, size)

    def scan(self, table_name, table_doc):
        struct_code, struct_size = self.struct_info[table_name]
        
        with open(table_doc['file'], "rb") as f:
            while row := f.read(struct_size):
                
                data = struct.unpack(struct_code, row)

                out = []
                # for i in char_ids:
                for i, col in enumerate(table_doc['columns']):
                    if col['type'] == 'char':
                        out.append(data[i].rstrip(b"\x00").decode())
                    else:
                        out.append(data[i])

                out = tuple(out)

                yield out

    def eval_where(self, row):
        def recursive_check(el):
            if isinstance(el, (AND, OR)):
                l = recursive_check(el.left)
                r = recursive_check(el.right)

                if isinstance(el, AND):
                    return (l and r)
                else:
                    return (l or r)

            else:
                l, r, op = el.left, el.right, el.op

                if isinstance(l, Column):
                    l = row[l.index]
                else:
                    l = l.val

                if isinstance(r, Column): 
                    r = row[r.index]
                else:
                    r = r.val                    
     
                return OPERATOR_DICT[op](l, r)
            

        tree = self.where
        if tree:
            eval = recursive_check(tree)
            return eval
        else: return True

    def run(self, query):

        if isinstance(query, Select):
            return self.run_select(query)
        elif isinstance(query, Insert):
            return self.run_insert(query)
        else:
            raise NotImplementedError()



    def run_insert(self, query):
                
        """
        1. Get the table's info from the catalog: its file, and its format string from the same code that builds it for the scan, so reading and writing always match
        2. Convert the values to their stored form. This is the reverse of the scan's cleanup: char values are encoded from str to bytes, and ints stay as they are. struct pads short byte strings with zeros automatically.
        3. Pack the values into a row of bytes with the format string
        4. Append the bytes to the end of the file, opening it in binary append mode ("ab")
        5. Report the result. Databases usually return a count, like INSERT 0 1 in Postgres or "1 row inserted", not rows.
        """

        table = query.to
        values = query.values
        table_schema = self.schema['tables'][table.table]

        print(table)
        print(values)
        print(table_schema)


    def run_select(self, query):
        queried_tables = [query.from_] # needs fix when multiple tabels
        self.tables = {}
        self.where = query.where
        for table in queried_tables:
            self.tables[table.table] = self.schema['tables'][table.table]

        self.create_struct_strings()
        yield [col.col for col in query.columns]
        for table_name, table_doc in self.tables.items():
            for x in self.scan(table_name, table_doc):
                eval = self.eval_where(x)
                if eval:
                    yield tuple(x[i] for i in [col.index for col in query.columns])

# query = """ SELECT id FROM users where id != 1"""
query = """ insert into users values (1, 2, 'joni') """


executor = Executor()
tokenizer = Tokenizer()
parser = Parser()
binder = Binder()

tokens = tokenizer.tokenize(query)
parsed_tokens = parser.parse(tokens)

query_tree = binder.bind(parsed_tokens)
for row in executor.run(query_tree):
    print(row)






"""
1. Consolidate what you have (small, but it pays off for everything after)
- A REPL: a loop that reads a query, runs it and prints the result as a table. Catch your own errors and print them instead of crashing, so one bad query doesn't end the session.
- Split yavin.py into modules: tokenizer, parser (with the AST classes), binder, executor, catalog, and a main/REPL file. The __main__ guard problem disappears with this too.
- One shared catalog object instead of the duplicated get_schema
- Tests for the parser, binder and executor. Precedence, error cases, * expansion, and actual result rows from a small test table. I can write them like the tokenizer tests if you want.

2. Make the database writable. Right now data only comes in through create_file.py.
- INSERT INTO users VALUES (4, 22, 'maija'): new tokens (INSERT, INTO, VALUES, parentheses), a new Insert AST node, binder checks (column count, types, string length vs char(n)), and the executor packs the row and appends it to the file.
- CREATE TABLE t (id INT, name CHAR(16)): adds a table to the catalog and creates an empty file. After this, the catalog is managed by your database instead of by hand.

3. Then the real database internals, from the reading list:
- Pages: store rows in fixed 4 KB pages instead of a flat file. This is the foundation for everything below.
- DELETE / UPDATE: introduce tombstones or slotted pages and free space
- A B+ tree index: WHERE id = 42 without scanning every row. This is the "find a record efficiently from the mass of data" problem from your README, and the most important topic on the list.
- Buffer pool: cache pages in memory instead of reading them from disk every time

Also possible at any point: ORDER BY, LIMIT, parentheses in WHERE, joins. These are smaller features that reuse what you already built.

I'd do the REPL and INSERT next, so you can use your database interactively and add data through SQL. Then pages and the B+ tree, which is where the interesting database problems start.


"""