import argparse
import re
from difflib import SequenceMatcher
from typing import List, Tuple

from parseerror import ParseError

KEYWORDS_BOUNDARY_AFTER = ['program', 'begin', 'end', 'var', 'print', 'println', 'get', 'while', 'if', 'then', 'else',
                           'or', 'and', 'not', 'true', 'false', 'procedure', 'return']
KEYWORDS_NO_BOUNDARY_AFTER = [";", ":=", "+", "-", "*", "/", "(", ")", "<=", ">=", "==", "<", ">", ","]

SPECIAL_TOKENS = [
    {
        "name": "NUMBER",
        "regex": r"\d+"
    },
    {
        "name": "ID_PAREN",
        "regex": r"[a-zA-Z]\w*\("
    },
    {
        "name": "ID",
        "regex": r"[a-zA-Z]\w*"
    },
    {
        "name": "STRING",
        "regex": r'''(?:'(?P<single_quote>[^']*)')|(?:"(?P<double_quote>[^"]*)")''',
        # if the regex matches, go through this list of capture groups and set the Token attribute to first matched one
        "group_priority": ["single_quote", "double_quote"]
    },
    {
        "name": "COMMENT",
        "regex": r"{-(?:[^-]|(?!))*-}"
    }
]


class Token:
    def __init__(self, name, attribute=None, line_num=None, col_num=None):
        self.name = name
        self.attribute = attribute
        self.line_num = line_num
        self.col_num = col_num
        self.context_line = None

        if attribute:
            assert (isinstance(attribute, str))

    def __repr__(self):
        return self.name + (f"({self.attribute})" if self.attribute else "")

    def __eq__(self, other):
        return self.name == other.name and self.attribute == other.attribute


def lex(lex_input: str):
    tokens: List[Token] = []
    index = 0
    line_num = 1
    index_at_start_of_line = 0
    lines = lex_input.split("\n")

    while index < len(lex_input):
        # ignore whitespace
        if lex_input[index].isspace():
            if lex_input[index] == "\n":
                line_num += 1
                index_at_start_of_line = index
                this_line_content = lines.pop(0)
                for token in tokens:
                    if token.context_line is None:
                        token.context_line = this_line_content
            index += 1
            continue

        # look for keywords
        remaining_input = lex_input[index:]
        index, keyword_found = _get_keyword(index, remaining_input, tokens, line_num,
                                            col_num=index - index_at_start_of_line)
        if keyword_found:
            continue

        # look for special tokens
        index, special_token_found = _get_special_token(index, remaining_input, tokens, line_num,
                                                        col_num=index - index_at_start_of_line)
        if special_token_found:
            continue

        else:
            # nothing found: error
            message = _get_parse_error_message(remaining_input)
            raise ParseError(message, line_num, index - index_at_start_of_line + 1, lines[0],
                             is_lex_error=True)

    this_line_content = lines.pop(0)
    for token in tokens:
        if token.context_line is None:
            token.context_line = this_line_content

    return tokens


def _get_keyword(index, remaining_input, tokens, line_num, col_num) -> Tuple[int, bool]:
    for keyword in KEYWORDS_NO_BOUNDARY_AFTER + KEYWORDS_BOUNDARY_AFTER:
        boundary = r"\b" if keyword in KEYWORDS_BOUNDARY_AFTER else ""
        if re.match(re.escape(keyword) + boundary, remaining_input):
            tokens.append(Token(keyword.upper(), line_num=line_num, col_num=col_num))
            index += len(keyword)
            return index, True

    return index, False


# returns (updated index, True iff keyword was found)
def _get_special_token(index, remaining_input, tokens, line_num, col_num):
    for special_token in SPECIAL_TOKENS:
        match = re.match(special_token["regex"], remaining_input)
        if match:
            token_attribute = match.group()
            if "group_priority" in special_token:
                for group_name in special_token['group_priority']:
                    if match.group(group_name):
                        token_attribute = match.group(group_name)
                        break

            if special_token["name"] != "COMMENT":
                tokens.append(Token(special_token["name"], token_attribute, line_num=line_num, col_num=col_num))
            index += len(match.group())
            return index, True

    return index, False


# returns (updated index, True iff special token was found)
def _get_parse_error_message(remaining_input):
    message = "unrecognised token"
    if remaining_input[0] in ["'", '"']:
        message = "unclosed string"
    elif remaining_input.startswith("{-"):
        message = "unclosed comment"
    else:
        next_word = remaining_input.split()[0]
        all_keywords = KEYWORDS_BOUNDARY_AFTER + KEYWORDS_NO_BOUNDARY_AFTER
        fuzzy_matchness = {k.lower(): SequenceMatcher(None, k.lower(), next_word).ratio() for k in all_keywords}
        best_match_keyword = max(fuzzy_matchness, key=fuzzy_matchness.get)
        if fuzzy_matchness[best_match_keyword] > 0.5:
            message += f" - did you mean '{best_match_keyword}'?"
    return message


def lex_and_join_with_newlines(s):
    return "\n".join(map(str, lex(s)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform lexical analysis")
    parser.add_argument("source", help="String to lex")
    args = parser.parse_args()
    print(lex_and_join_with_newlines(args.source))
