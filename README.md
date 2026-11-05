# Learning what is database




## Notes


database


database -- database managemetn system (get data based on query) -- userinterface


- standard sql
- how do we store the data
    - metadata
- how do we get the data based on sql


- problem is that how do we get certain record / datapoint efficiently from the mass of data
    - 

- what is the fileformat for the data
    - how is the data inside the files


Putting data into permanent storage is generally the responsibility of the database engine a.k.a. "storage engine". Though typically accessed by a DBMS through the underlying operating system (and often using the operating systems' file systems as intermediates for storage layout)


storage is divided into pages for example 4kb
    - this because disks and os reads in blocks
    - we can read whole block at the sam time

diffentet databases have different way of organizing files
    - sqlite: whole db in single file
    - postgres: roughly one file per table


parsing
- define the commands (select, from, where)
1. cut based on commands in the incoming query
2. make sure it contains minimal commands
3. parse each cut
    1. select: make sure contians comma seperated list of words, pack into list of selected columns (transformations later)
    2. from: make sure contains a single word for now (no renaming), pack into table name
    3. where: make sure contains and seperated list of operations
        for each opreation: make sure has operand, operator and another operand
        pack into list of jsons (col: , op: , val:)




storage
- binary, fixed-length rows (e.g. int = 4 bytes, text = fixed 32 bytes). Row N then sits at offset N * row_size.
- .tbl files
-  One file per table, e.g. users.tbl, plus one schema/metadata file (e.g. users.schema listing column names and types)
- stored as binary
    - Python: the struct module, e.g. struct.pack("<ii8s", 1, 30, b"bob"). < means little-endian.


parser
- at first only support select statements
- tokenizer (lexer) turns string into tokens (select, comma, from, star, where)
- parserturns tokesn into objects
    - Query { columns: ["name","age"], table: "users", where: {col:"age", op:"=", value:5} }
-  recursive descent parser,. Abstract syntax tree


executor
1. read schema 
2. scan full table
3. keep only rows based on the filter
4. print resutl





--- claude notes

Overall architecture
- DBMS architecture layers: parser → planner/optimizer → executor → storage engine
- Client/server model and wire protocols (how a UI talks to the DBMS)

"Standard SQL"
- Relational model and relational algebra (select, project, join)
- SQL grammar: tokenizing/lexing, parsing, abstract syntax trees (AST)
- Recursive descent parsers
- DDL vs DML (CREATE TABLE vs SELECT/INSERT/UPDATE/DELETE)

"How do we store the data" / "file format"
- Pages / blocks: fixed-size pages, usually 4–16 KB
- Slotted page layout
- Heap files
- Record/tuple format: fixed-length vs variable-length fields, NULL bitmaps
- Row-oriented vs column-oriented storage
- Serialization and endianness
- SQLite file format (a well-documented, readable real-world example)

"Metadata"
- System catalog / data dictionary (where table schemas, columns and indexes are stored)
- Schemas and data types

"Getting a certain record efficiently from the mass of data"
- Indexes in general: clustered vs non-clustered, primary vs secondary
- B-trees and B+ trees (the most important topic on this list)
- Hash indexes
- LSM trees (the alternative to B-trees, used in RocksDB and LevelDB)
- Full table scan vs index scan

"How do we get the data based on SQL"
- Query planning and query optimization
- Cost-based optimization, statistics, selectivity
- Join algorithms: nested loop, hash join, sort-merge join
- Execution models: the iterator ("Volcano") model, vectorized execution
- External sorting (sorting data that doesn't fit in memory)

Storage engine / OS interaction
- Buffer pool / buffer manager and page caching
- Page replacement policies: LRU, clock
- mmap vs your own buffer pool (and why many databases avoid mmap)
- fsync, O_DIRECT, the OS page cache

Reliability (once the basics work)
- Transactions and ACID
- Write-ahead logging (WAL)
- Crash recovery (ARIES)
- Concurrency control: locking, two-phase locking (2PL), MVCC
- Isolation levels



1. Storage: start almost stupidly simple
- One file per table, e.g. users.tbl, plus one schema/metadata file (e.g. users.schema listing column names and types)
- Option A, easiest: CSV-like text, one row per line. You can open it and see what's going on.
- Option B, a step toward real databases: binary, fixed-length rows (e.g. int = 4 bytes, text = fixed 32 bytes). Row N then sits at offset N * row_size.
- Start with A and move to B later.
- Read about: fixed vs variable-length records, serialization

2. Parser: support only one shape of query
SELECT col1, col2 FROM table WHERE col = value;
SELECT * FROM table;
- Tokenizer (lexer): turns the string into tokens like SELECT, IDENT(name), COMMA, FROM, STAR, WHERE, EQ, NUMBER(5), STRING('bob')
- Parser: turns tokens into a struct/object, for example:
Query { columns: ["name","age"], table: "users", where: {col:"age", op:"=", value:5} }
- A hand-written recursive descent parser is perfect for this. Don't use parser generators yet.
- Read about: lexing/tokenizing, recursive descent parsing, AST

3. Executor: turn the parsed query into results
- Read the schema for the table, so you know the column names, types and order
- Full table scan: read every row
- Filter: keep rows where the WHERE condition is true
- Projection: keep only the requested columns
- Print the results as a table
- Read about: full table scan, selection and projection in relational algebra, and later the iterator (Volcano) model, which is a nice way to structure scan → filter → project

4. Getting data in
- Without INSERT you need some way to add rows. Either write the file by hand at first, or make INSERT INTO t VALUES (...) your second statement. It reuses the same tokenizer.

5. Simple REPL as the "user interface"
- Loop: read a line → tokenize → parse → execute → print

Order to build it:
1. Hand-write a data file and a schema file
2. Code that reads and prints the whole table (scan)
3. Tokenizer, tested on its own
4. Parser for SELECT * FROM t
5. Add the column list (projection)
6. Add WHERE col = value (filter)
7. REPL around it
8. INSERT
