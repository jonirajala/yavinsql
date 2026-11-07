"""Tokenizer tests.

Run with:  python -m unittest test_parser -v

Conventions these tests assume (change them if you decide differently):
- Each token is compared as (type, value, pos).
- pos = index of the token's first character in the query
  (for strings: the opening quote).
- Keyword tokens keep the original text as value ('select' stays 'select').
- Both '...' and "..." are strings (current design). No escaping yet:
  a string ends at the first quote matching the opening one.
- Operator combinations like =< or <=< are valid tokens; rejecting them
  is the parser's job.
- Every token list ends with exactly one EOF token, at pos = len(query).
  Most tests check that and then compare the tokens before it.
- Invalid input raises ValueError. A crash with another exception
  (IndexError, KeyError...) counts as a failure.
"""

import unittest

from yavin import Tokenizer, Tokentype as T


def strip_eof(tokens):
    """Check the list ends with exactly one EOF token, then drop it."""
    assert tokens, "token list is empty, expected at least EOF"
    assert tokens[-1].type == T.EOF, f"last token is {tokens[-1].type}, expected EOF"
    assert all(t.type != T.EOF for t in tokens[:-1]), "EOF appears before the end"
    return [(t.type, t.value, t.pos) for t in tokens[:-1]]


def toks(query):
    return strip_eof(Tokenizer().tokenize(query))


class TestWords(unittest.TestCase):
    def test_select_star(self):
        self.assertEqual(toks("SELECT * FROM users"), [
            (T.SELECT, "SELECT", 0),
            (T.STAR, "*", 7),
            (T.FROM, "FROM", 9),
            (T.IDENTIFIER, "users", 14),
        ])

    def test_column_list_no_spaces(self):
        self.assertEqual(toks("SELECT id,name FROM t"), [
            (T.SELECT, "SELECT", 0),
            (T.IDENTIFIER, "id", 7),
            (T.COMMA, ",", 9),
            (T.IDENTIFIER, "name", 10),
            (T.FROM, "FROM", 15),
            (T.IDENTIFIER, "t", 20),
        ])

    def test_star_no_spaces(self):
        self.assertEqual(toks("SELECT*FROM t"), [
            (T.SELECT, "SELECT", 0),
            (T.STAR, "*", 6),
            (T.FROM, "FROM", 7),
            (T.IDENTIFIER, "t", 12),
        ])

    def test_lowercase_keywords(self):
        self.assertEqual(toks("select x from y"), [
            (T.SELECT, "select", 0),
            (T.IDENTIFIER, "x", 7),
            (T.FROM, "from", 9),
            (T.IDENTIFIER, "y", 14),
        ])

    def test_mixed_case_keywords(self):
        self.assertEqual(toks("SeLeCt x FrOm y"), [
            (T.SELECT, "SeLeCt", 0),
            (T.IDENTIFIER, "x", 7),
            (T.FROM, "FrOm", 9),
            (T.IDENTIFIER, "y", 14),
        ])

    def test_identifiers_with_digits_and_underscores(self):
        self.assertEqual(toks("SELECT col_1,_tmp FROM t2"), [
            (T.SELECT, "SELECT", 0),
            (T.IDENTIFIER, "col_1", 7),
            (T.COMMA, ",", 12),
            (T.IDENTIFIER, "_tmp", 13),
            (T.FROM, "FROM", 18),
            (T.IDENTIFIER, "t2", 23),
        ])

    def test_keyword_prefix_is_identifier(self):
        self.assertEqual(toks("SELECT selected FROM fromage"), [
            (T.SELECT, "SELECT", 0),
            (T.IDENTIFIER, "selected", 7),
            (T.FROM, "FROM", 16),
            (T.IDENTIFIER, "fromage", 21),
        ])

    def test_and_or(self):
        self.assertEqual(toks("WHERE a = 1 AND b = 2 OR c = 3"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "a", 6),
            (T.EQ, "=", 8),
            (T.INT, 1, 10),
            (T.AND, "AND", 12),
            (T.IDENTIFIER, "b", 16),
            (T.EQ, "=", 18),
            (T.INT, 2, 20),
            (T.OR, "OR", 22),
            (T.IDENTIFIER, "c", 25),
            (T.EQ, "=", 27),
            (T.INT, 3, 29),
        ])


class TestNumbers(unittest.TestCase):
    def test_number_at_end(self):
        self.assertEqual(toks("WHERE age = 30"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "age", 6),
            (T.EQ, "=", 10),
            (T.INT, 30, 12),
        ])

    def test_no_spaces(self):
        self.assertEqual(toks("WHERE age=30"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "age", 6),
            (T.EQ, "=", 9),
            (T.INT, 30, 10),
        ])

    def test_numbers_with_comma(self):
        self.assertEqual(toks("SELECT 1,2 FROM t"), [
            (T.SELECT, "SELECT", 0),
            (T.INT, 1, 7),
            (T.COMMA, ",", 8),
            (T.INT, 2, 9),
            (T.FROM, "FROM", 11),
            (T.IDENTIFIER, "t", 16),
        ])

    def test_zero(self):
        self.assertEqual(toks("WHERE a = 0")[-1], (T.INT, 0, 10))

    def test_leading_zeros(self):
        self.assertEqual(toks("WHERE a = 007")[-1], (T.INT, 7, 10))

    def test_decimal_is_error(self):
        with self.assertRaises(ValueError):
            toks("WHERE x = 3.5")

    def test_number_followed_by_letters_is_error(self):
        with self.assertRaises(ValueError):
            toks("WHERE x = 30abc")


class TestOperators(unittest.TestCase):
    def test_lt(self):
        self.assertEqual(toks("WHERE a < 1"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "a", 6),
            (T.LT, "<", 8),
            (T.INT, 1, 10),
        ])

    def test_gt(self):
        self.assertEqual(toks("WHERE a > 1"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "a", 6),
            (T.GT, ">", 8),
            (T.INT, 1, 10),
        ])

    def test_lte(self):
        self.assertEqual(toks("WHERE a <= 1"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "a", 6),
            (T.LTE, "<=", 8),
            (T.INT, 1, 11),
        ])

    def test_gte_no_spaces(self):
        self.assertEqual(toks("WHERE a>=1"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "a", 6),
            (T.GTE, ">=", 7),
            (T.INT, 1, 9),
        ])

    def test_neq_angle(self):
        self.assertEqual(toks("WHERE a <> b"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "a", 6),
            (T.NEQ, "<>", 8),
            (T.IDENTIFIER, "b", 11),
        ])

    def test_neq_bang(self):
        self.assertEqual(toks("WHERE a != b"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "a", 6),
            (T.NEQ, "!=", 8),
            (T.IDENTIFIER, "b", 11),
        ])

    def test_operator_at_end(self):
        self.assertEqual(toks("WHERE a <"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "a", 6),
            (T.LT, "<", 8),
        ])

    def test_reversed_operator_is_two_tokens(self):
        self.assertEqual(toks("WHERE a =< 1"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "a", 6),
            (T.EQ, "=", 8),
            (T.LT, "<", 9),
            (T.INT, 1, 11),
        ])

    def test_longest_match_first(self):
        self.assertEqual(toks("WHERE a <=< 21"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "a", 6),
            (T.LTE, "<=", 8),
            (T.LT, "<", 10),
            (T.INT, 21, 12),
        ])

    def test_lone_bang_is_error(self):
        with self.assertRaises(ValueError):
            toks("WHERE a ! 1")

    def test_bang_at_end_is_error(self):
        with self.assertRaises(ValueError):
            toks("WHERE a !")

    def test_minus_is_error(self):
        with self.assertRaises(ValueError):
            toks("WHERE a <-1")


class TestStrings(unittest.TestCase):
    def test_simple_string(self):
        self.assertEqual(toks("WHERE name = 'bob'"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "name", 6),
            (T.EQ, "=", 11),
            (T.STRING, "bob", 13),
        ])

    def test_string_followed_by_more(self):
        self.assertEqual(toks("WHERE name = 'bob' AND age = 1"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "name", 6),
            (T.EQ, "=", 11),
            (T.STRING, "bob", 13),
            (T.AND, "AND", 19),
            (T.IDENTIFIER, "age", 23),
            (T.EQ, "=", 27),
            (T.INT, 1, 29),
        ])

    def test_empty_string(self):
        self.assertEqual(toks("WHERE name = ''"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "name", 6),
            (T.EQ, "=", 11),
            (T.STRING, "", 13),
        ])

    def test_keeps_spaces(self):
        self.assertEqual(toks("WHERE s = ' a '")[-1], (T.STRING, " a ", 10))

    def test_keywords_and_symbols_inside(self):
        self.assertEqual(toks("WHERE s = 'select, * from'"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "s", 6),
            (T.EQ, "=", 8),
            (T.STRING, "select, * from", 10),
        ])

    def test_double_quotes_inside_single(self):
        self.assertEqual(toks("WHERE name = 'say \"hi\"'"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "name", 6),
            (T.EQ, "=", 11),
            (T.STRING, 'say "hi"', 13),
        ])

    def test_double_quoted_string(self):
        self.assertEqual(toks('WHERE s = "bob"')[-1], (T.STRING, "bob", 10))

    def test_single_quote_inside_double(self):
        self.assertEqual(toks('WHERE s = "it\'s"')[-1], (T.STRING, "it's", 10))

    def test_unterminated_string_is_error(self):
        with self.assertRaises(ValueError):
            toks("WHERE name = 'bob")

    def test_lone_quote_is_error(self):
        with self.assertRaises(ValueError):
            toks("'")

    def test_mismatched_quotes_is_error(self):
        with self.assertRaises(ValueError):
            toks("WHERE name = 'bob\"")


class TestWhitespace(unittest.TestCase):
    def test_empty_query(self):
        self.assertEqual(toks(""), [])

    def test_only_spaces(self):
        self.assertEqual(toks("   "), [])

    def test_leading_and_trailing_spaces(self):
        self.assertEqual(toks("  SELECT x  "), [
            (T.SELECT, "SELECT", 2),
            (T.IDENTIFIER, "x", 9),
        ])

    def test_tabs_and_newlines(self):
        self.assertEqual(toks("SELECT\tx\nFROM t"), [
            (T.SELECT, "SELECT", 0),
            (T.IDENTIFIER, "x", 7),
            (T.FROM, "FROM", 9),
            (T.IDENTIFIER, "t", 14),
        ])


class TestSingleCharQueries(unittest.TestCase):
    def test_star(self):
        self.assertEqual(toks("*"), [(T.STAR, "*", 0)])

    def test_letter(self):
        self.assertEqual(toks("a"), [(T.IDENTIFIER, "a", 0)])

    def test_digit(self):
        self.assertEqual(toks("7"), [(T.INT, 7, 0)])

    def test_operator(self):
        self.assertEqual(toks("="), [(T.EQ, "=", 0)])


class TestUnknownCharacters(unittest.TestCase):
    def test_hash(self):
        with self.assertRaises(ValueError):
            toks("SELECT # FROM t")

    def test_at(self):
        with self.assertRaises(ValueError):
            toks("SELECT @x FROM t")

    def test_unknown_at_end(self):
        with self.assertRaises(ValueError):
            toks("SELECT x FROM t#")


class TestFullQuery(unittest.TestCase):
    def test_realistic_query(self):
        q = "SELECT id, name FROM users WHERE age >= 18 AND name != 'bob'"
        self.assertEqual(toks(q), [
            (T.SELECT, "SELECT", 0),
            (T.IDENTIFIER, "id", 7),
            (T.COMMA, ",", 9),
            (T.IDENTIFIER, "name", 11),
            (T.FROM, "FROM", 16),
            (T.IDENTIFIER, "users", 21),
            (T.WHERE, "WHERE", 27),
            (T.IDENTIFIER, "age", 33),
            (T.GTE, ">=", 37),
            (T.INT, 18, 40),
            (T.AND, "AND", 43),
            (T.IDENTIFIER, "name", 47),
            (T.NEQ, "!=", 52),
            (T.STRING, "bob", 55),
        ])


class TestState(unittest.TestCase):
    def test_same_Tokenizer_twice(self):
        p = Tokenizer()
        p.tokenize("SELECT a")
        result = strip_eof(p.tokenize("FROM b"))
        self.assertEqual(result, [
            (T.FROM, "FROM", 0),
            (T.IDENTIFIER, "b", 5),
        ])


class TestEOF(unittest.TestCase):
    # EOF pos = len(query): one past the last character
    def test_eof_position(self):
        tokens = Tokenizer().tokenize("SELECT a")
        self.assertEqual(tokens[-1].type, T.EOF)
        self.assertEqual(tokens[-1].pos, 8)

    def test_eof_position_trailing_spaces(self):
        tokens = Tokenizer().tokenize("SELECT a  ")
        self.assertEqual(tokens[-1].pos, 10)

    def test_empty_query_is_only_eof(self):
        tokens = Tokenizer().tokenize("")
        self.assertEqual([(t.type, t.pos) for t in tokens], [(T.EOF, 0)])


if __name__ == "__main__":
    unittest.main()
