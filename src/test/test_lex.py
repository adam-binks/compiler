import os
import unittest

import lexer

from lexer import Token
from parseerror import ParseError
from test.common_test import get_data_dir


class TestLex(unittest.TestCase):
    def test_all_data(self):
        expect_fail = ["test7.oreo"]
        for filename in os.listdir(get_data_dir()):
            path = os.path.join(get_data_dir(), filename)
            if os.path.isfile(path):
                with open(path, "r") as f:
                    s = f.read()
                    if filename in expect_fail:
                        self.assertRaises(ParseError, lexer.lex, s)
                    else:
                        lexer.lex(s)  # just check no exceptions

    def test_assignment(self):
        tokens = lexer.lex("x := 10")
        self.assertEqual([Token("ID", "x"), Token(":="), Token("NUMBER", "10")], tokens)

    def test_multiline_keyword(self):
        tokens = lexer.lex("prog\nram")
        self.assertEqual([Token("ID", "prog"), Token("ID", "ram")], tokens)

    def test_unclosed_string(self):
        self.assertRaises(ParseError, lexer.lex, '''id := "an unclosed string then if;''')

    def test_unclosed_comment(self):
        self.assertRaises(ParseError, lexer.lex, '''id := "a string" {- an unclosed comment  then if;''')

    def test_adjacent_string_and_number(self):
        tokens = lexer.lex("program myprog 29'my string 22'1")
        self.assertEqual([Token("PROGRAM"), Token("ID", "myprog"), Token("NUMBER", "29"),
                          Token("STRING", "my string 22"), Token("NUMBER", "1")], tokens)

    def test_adjacent_string_and_number_double_quotes(self):
        tokens = lexer.lex('program myprog 29"my string 22"1')
        self.assertEqual([Token("PROGRAM"), Token("ID", "myprog"), Token("NUMBER", "29"),
                          Token("STRING", "my string 22"), Token("NUMBER", "1")], tokens)

    def test_nested_string_quote_double(self):
        tokens = lexer.lex('''program "blah 'blah' blah"''')
        self.assertEqual([Token("PROGRAM"), Token("STRING", "blah 'blah' blah")], tokens)

    def test_nested_string_quote_single(self):
        tokens = lexer.lex('''program 'blah "blah" blah' ''')
        self.assertEqual([Token("PROGRAM"), Token("STRING", '''blah "blah" blah''')], tokens)

    def test_id_prefixed_with_reserved(self):
        tokens = lexer.lex("programming := 10")
        self.assertEqual([Token("ID", "programming"), Token(":="), Token("NUMBER", "10")], tokens)

    def test_id_prefixed_and_suffixed_with_reserved(self):
        tokens = lexer.lex("truefalse")
        self.assertEqual([Token("ID", "truefalse")], tokens)

    def test_while_open_paren(self):
        tokens = lexer.lex("while(")
        self.assertEqual([Token("WHILE"), Token("(")], tokens)

    def test_ge(self):
        tokens = lexer.lex(">=")
        self.assertEqual([Token(">=")], tokens)
