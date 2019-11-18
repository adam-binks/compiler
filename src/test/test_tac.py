import os
import unittest

from grammarparse import parse_grammar_from_file
from semanticanalyser import semantic_analyse
from syntaxanalyser import parse_file
from tac import compile_to_tac
from test.common_test import get_data_dir, get_grammar_file
from typechecker import type_check


class TestTacCompiler(unittest.TestCase):
    def setUp(self):
        self.expansions = parse_grammar_from_file(get_grammar_file())

    def test_print_tac(self):
        parse_tree = parse_file(os.path.join(get_data_dir(), "simple.oreo"), self.expansions)
        semantic_analyse(parse_tree)
        type_check(parse_tree)
        # print(parse_tree.get_pretty_print_string(print_type=True))

        program = compile_to_tac(parse_tree)
        print("\nCOMPILE OUTPUT:\n" + repr(program))
        self.assertIsNotNone(parse_tree)
