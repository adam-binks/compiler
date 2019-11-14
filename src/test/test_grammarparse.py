import unittest

from grammarparse import parse_grammar, parse_grammar_from_file
from lexer import Token
from syntaxanalyser import Expansion, NonTerminal, Terminal
from test.common_test import get_grammar_file


class TestGrammarParse(unittest.TestCase):
    def test_parse_toy_grammar(self):
        expansions = parse_grammar([
            'x -> y | "A" "B"',
            'y -> "C"'
        ])

        self.assertEqual({
            NonTerminal("x"): [
                Expansion([NonTerminal("y")]),
                Expansion([Terminal(Token("A")), Terminal(Token("B"))])
            ],
            NonTerminal("y"): [
                Expansion([Terminal(Token("C"))])
            ]
        }, expansions)

    def test_parse_real_grammar(self):
        expansions = parse_grammar_from_file(get_grammar_file())

        self.assertIsNotNone(expansions)
