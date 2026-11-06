"""Tokenizer tests.

Run with:  python -m unittest test_parser -v

Conventions these tests assume (change them if you decide differently):
- Each token is compared as (type, value, pos).
- pos = index of the token's first character in the query
  (for strings: the opening quote).
- Keyword tokens keep the original text as value ('select' stays 'select').
- Invalid input raises ValueError. A crash with another exception
  (IndexError, KeyError...) counts as a failure.
"""

import unittest

from yavin import Parser, Tokentype as T


def toks(query):
    return [(t.type, t.value, t.pos) for t in Parser().tokenize(query)]


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

    def test_lowercase_keywords(self):
        self.assertEqual(toks("select x from y"), [
            (T.SELECT, "select", 0),
            (T.IDENTIFIER, "x", 7),
            (T.FROM, "from", 9),
            (T.IDENTIFIER, "y", 14),
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

    def test_decimal_is_error(self):
        with self.assertRaises(ValueError):
            toks("WHERE x = 3.5")

    def test_number_followed_by_letters_is_error(self):
        with self.assertRaises(ValueError):
            toks("WHERE x = 30abc")


class TestOperators(unittest.TestCase):
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
        # valid for the tokenizer; the parser rejects it later
        self.assertEqual(toks("WHERE a <"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "a", 6),
            (T.LT, "<", 8),
        ])

    def test_reversed_operator_is_error(self):
        with self.assertRaises(ValueError):
            toks("WHERE a =< 1")

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

    def test_escaped_quote(self):
        self.assertEqual(toks("WHERE name = 'it''s'"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "name", 6),
            (T.EQ, "=", 11),
            (T.STRING, "it's", 13),
        ])

    def test_double_quotes_inside_string(self):
        self.assertEqual(toks("WHERE name = 'say \"hi\"'"), [
            (T.WHERE, "WHERE", 0),
            (T.IDENTIFIER, "name", 6),
            (T.EQ, "=", 11),
            (T.STRING, 'say "hi"', 13),
        ])

    def test_unterminated_string_is_error(self):
        with self.assertRaises(ValueError):
            toks("WHERE name = 'bob")

    def test_mismatched_quotes_is_error(self):
        with self.assertRaises(ValueError):
            toks("WHERE name = 'bob\"")


class TestErrorsAndEdgeCases(unittest.TestCase):
    def test_unknown_char_hash(self):
        with self.assertRaises(ValueError):
            toks("SELECT # FROM t")

    def test_unknown_char_at(self):
        with self.assertRaises(ValueError):
            toks("SELECT @x FROM t")

    def test_empty_query(self):
        self.assertEqual(toks(""), [])

    def test_only_spaces(self):
        self.assertEqual(toks("   "), [])


if __name__ == "__main__":
    unittest.main()
