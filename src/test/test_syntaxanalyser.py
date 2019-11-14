import os
import unittest

from grammarparse import parse_grammar_from_file
from parseerror import ParseError
from syntaxanalyser import syntax_analyse, parse_file
from lexer import lex
from test.common_test import get_data_dir, get_grammar_file


class TestSyntaxAnalyser(unittest.TestCase):
    def setUp(self):
        self.expansions = parse_grammar_from_file(get_grammar_file())

    def test_parse_files(self):
        expect_fail_lex = ["test7.oreo"]

        # map from filename to line number where parse error should be generated
        expect_fail_syntax = {
            "test2.oreo": 12,
            "test3.oreo": 10,
            "test4.oreo": 17,
            "test5.oreo": 25,
            "test9.oreo": 19,
            "test10.oreo": 10,
            "return_outside_function.oreo": 14,
            "nested_function.oreo": 8,
            "illegal_expression.oreo": 9,
            "more_after_end.oreo": 26
        }

        for filename in sorted(os.listdir(get_data_dir())):
            if filename in expect_fail_lex:
                continue

            path = os.path.join(get_data_dir(), filename)
            if os.path.isfile(path):
                with self.subTest(filename):
                    if filename in expect_fail_syntax.keys():
                        try:
                            parse_file(path, self.expansions)

                            self.fail(f"{filename} should have failed on line {expect_fail_syntax[filename]}, but passed")
                        except ParseError as e:
                            self.assertEqual(e.line_num, expect_fail_syntax[filename])
                    else:
                        self.assertIsNotNone(parse_file(path, self.expansions))

    def test_print_parse_tree(self):
        parse_tree = syntax_analyse(lex("program prog begin print x >= y; end"), self.expansions)
        print(parse_tree.get_pretty_print_string())
        self.assertIsNotNone(parse_tree)
