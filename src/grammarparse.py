from collections import defaultdict
from typing import List

from lexer import Token
from syntaxanalyser import Expansion, NonTerminal, Terminal


def get_expansion(rule_str):
    rule_str = rule_str.split("#")[0]  # discard any content after #
    tokens = rule_str.split()

    if tokens == ["ε"]:
        return Expansion(None)

    rule = []
    is_zero_or_more = False
    for token in tokens:
        token = token.strip()
        if token.startswith('"') and token.endswith('"'):
            assert(len(token) > 2)
            rule.append(Terminal(Token(token[1:-1])))
        else:
            if token.endswith("*"):
                token = token[:-1]
                is_zero_or_more = True
            rule.append(NonTerminal(token, is_zero_or_more))

    return Expansion(rule)


def parse_grammar_from_file(filename):
    with open(filename, "r") as f:
        lines = f.readlines()

    return parse_grammar(lines)


def parse_grammar(lines: List[str]):
    expansions = defaultdict(list)
    for line in lines:
        lhs, rhs = line.split("->")
        expansions[NonTerminal(lhs.strip())] = [get_expansion(s) for s in rhs.split('|')]

    for expansions_by_lhs in expansions.values():
        for expansion in expansions_by_lhs:
            if expansion.rhs is not None:
                for x in expansion.rhs:
                    assert isinstance(x, Terminal) or x in expansions.keys(),\
                        f"{x} does not have an expansion"

    return dict(expansions)
