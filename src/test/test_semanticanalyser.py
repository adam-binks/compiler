import os
import unittest

from grammarparse import parse_grammar_from_file
from semanticanalyser import semantic_analyse
from syntaxanalyser import parse_file
from test.common_test import get_data_dir, get_grammar_file


class TestSemanticAnalyser(unittest.TestCase):
    def setUp(self):
        self.expansions = parse_grammar_from_file(get_grammar_file())

    def test_print_parse_tree(self):
        parse_tree = parse_file(os.path.join(get_data_dir(), "sem_good.oreo"), self.expansions)
        semantic_analyse(parse_tree)
        print(parse_tree.get_pretty_print_string(print_scope=False))

        missing = [n for n in parse_tree.get_children_breadth_first() if not hasattr(n, "scope")]
        self.assertEqual([], missing)

