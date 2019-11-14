"""Entry point for commmand line interaction

Usage: python3 parser.py <FILENAME> [--grammar <GRAMMAR FILENAME>]
"""

import argparse
import os

from grammarparse import parse_grammar_from_file
from parseerror import ParseError
from syntaxanalyser import parse_file

if __name__ == "__main__":
    oreo_grammar = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "oreo.grammar")

    parser = argparse.ArgumentParser(description="Parse the given file and print the parse tree")
    parser.add_argument("file", help="File path to parse")
    parser.add_argument("--grammar", '-g', default=oreo_grammar, help="File containing a valid grammar")
    args = parser.parse_args()

    parsed_expansions = parse_grammar_from_file(args.grammar)
    try:
        print(parse_file(args.file, parsed_expansions).get_pretty_print_string())
    except ParseError as e:
        print(e.message)
