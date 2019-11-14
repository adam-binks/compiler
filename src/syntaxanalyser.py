import copy
import math
from typing import List, Union, Dict

from colours import BLUE, YELLOW, RESET_COLOUR
from lexer import Token, lex
from parseerror import ParseError

# for pretty printing
PADDING = 1 * " "
LINE_VERTICAL = "╦"
LINE_VERT_LEFTMOST = "╔"
LINE_VERT_RIGHTMOST = "╗"
LINE_VERT_ONLY = "║"
LINE_VERTICAL_UPWARDS = "╩"
LINE_CROSS = "╬"
LINE_HORIZONTAL = "═"


class Terminal:
    def __init__(self, token: Token):
        self.token = token

    def __eq__(self, other):
        return other.token.name == self.token.name

    def __repr__(self):
        return repr(self.token)


class NonTerminal:
    def __init__(self, name: str, is_zero_or_more=False):
        self.name = name
        self.is_zero_or_more = is_zero_or_more

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return other.name == self.name

    def __repr__(self):
        return f"{self.name}"


class Expansion:
    def __init__(self, rhs: Union[List[Union[Terminal, NonTerminal]], None]):
        self.rhs = rhs

    def __repr__(self):
        if self.rhs is None:
            return "<ε>"
        return "<" + " ".join(repr(x) for x in self.rhs) + ">"

    def __eq__(self, other):
        return len(other.rhs) == len(self.rhs) \
               and all([self.rhs[i] == other.rhs[i] for i in range(len(self.rhs))])


class ParseTreeNode:
    def __init__(self, content: Union[NonTerminal, Terminal], parent=None):
        self.content = content
        self.children: List[ParseTreeNode] = []
        self.parent = parent
        self.processed = False
        self.destroy = False

        if parent:
            self.level = parent.level + 1
        else:
            self.level = 0

    def __repr__(self):
        return repr(self.content)

    def parse_tokens(self, tokens: List[Token], expansions):
        prev_token = None

        while True:
            node = self.get_next_node()
            self.handle_eof_errors(node, prev_token, tokens)
            if node is None:
                return
            prev_token = tokens[0]

            if isinstance(node.content, NonTerminal):
                # expand the non terminal
                node._expand(tokens, expansions)

            else:
                # compare the expected terminal to actual next token
                if node.content.token.name == tokens[0].name:
                    node.content.token = tokens.pop(0)
                    node.processed = True
                else:
                    raise ParseError(f"expected '{repr(node.content).lower()}', got '{repr(tokens[0]).lower()}'",
                                     tokens[0].line_num, tokens[0].col_num, tokens[0].context_line)

    def handle_eof_errors(self, node, prev_token, tokens):
        if node is None:
            if tokens:
                raise ParseError(f"expected END OF FILE, got '{repr(tokens[0]).lower()}'",
                                 tokens[0].line_num, tokens[0].col_num, tokens[0].context_line)
            return

        if not tokens:
            # EOF reached unexpectedly
            if prev_token:
                line_num = prev_token.line_num
                col_num = len(prev_token.context_line.rstrip())
                context_line = prev_token.context_line
            else:
                # the file was empty
                line_num, col_num, context_line = 0, 0, "<No content to parse>"
            raise ParseError(f"expected '{repr(node.content).lower()}', got END OF FILE",
                             line_num, col_num, context_line)

    def get_next_node(self):
        if not self.processed:
            return self

        self.children = [c for c in self.children if not c.destroy]

        for child in self.children:
            child_node = child.get_next_node()
            if child_node is not None:
                return child_node

        return None

    def _expand(self, tokens, expansions):
        assert (isinstance(self.content, NonTerminal))

        expansion = find_expansion(self.content, tokens[0], expansions)
        if not expansion:
            if self.content.is_zero_or_more:
                self.destroy = True
                return
            else:
                nonterminal_str = repr(self.content).replace("_", " ")
                raise ParseError(f"expected a valid {nonterminal_str}, got '{repr(tokens[0]).lower()}'",
                                 tokens[0].line_num, tokens[0].col_num, tokens[0].context_line)
        self.processed = True

        # if this non terminal has a Kleene star, add an optional sibling with the same non terminal and Kleene star
        if self.content.is_zero_or_more:
            duplicate = ParseTreeNode(NonTerminal(self.content.name, is_zero_or_more=True), self.parent)
            self.parent.children.insert(self.parent.children.index(self) + 1, duplicate)

        if isinstance(expansion, str) and expansion == "ε":
            self.destroy = True
        else:
            self.children = [ParseTreeNode(copy.deepcopy(x), parent=self) for x in expansion.rhs]
            self.children[0].content.token = tokens[0]

    def get_pretty_print_string(self):
        output = []
        line = YELLOW
        edges_line = BLUE
        prev_node = None
        level = 0
        breadth_first = self.get_children_breadth_first()
        for node in breadth_first:
            if node.level != level:
                level = node.level
                if node.level > 1:
                    output.append(edges_line + RESET_COLOUR)
                output.append(line + RESET_COLOUR)
                line = YELLOW
                edges_line = BLUE
                prev_node = None

            if node.parent:
                while len(line) < node.parent.left_col:
                    line += " "

            edges_line, line = self._update_line_and_edge_line(edges_line, line, node, prev_node)

            prev_node = node

        output.append(edges_line + RESET_COLOUR)
        output.append(line + RESET_COLOUR)

        return "\n".join(output)

    def _update_line_and_edge_line(self, edges_line, line, node, prev_node):
        edge_char = LINE_HORIZONTAL if prev_node and prev_node.parent == node.parent else " "

        node.left_col = len(line)

        line += math.floor(node.get_string_width() / 2 - len(repr(node.content)) / 2) * " "
        node.repr_col = len(line) + len(PADDING) + math.ceil(len(repr(node.content)) / 2)
        content = PADDING + repr(node.content) + PADDING
        line += content

        edges_line += math.ceil(len(line) - len(edges_line) - len(content) / 2 - 1) * edge_char
        edges_line += self._get_vertical_char(node)

        line += math.floor(node.get_string_width() / 2 - len(repr(node.content)) / 2) * " "
        node.right_col = len(line)
        edges_line = self._draw_link_to_parent(edges_line, node)

        return edges_line, line

    def _draw_link_to_parent(self, edges_line, node):
        if node.parent and node == node.parent.children[-1] and len(node.parent.children) > 1:
            if node.parent.repr_col < len(edges_line) and edges_line[node.parent.repr_col] == LINE_VERTICAL:
                connector_char = LINE_CROSS
            else:
                connector_char = LINE_VERTICAL_UPWARDS
            edges_line = edges_line[0:node.parent.repr_col - 1] + connector_char \
                + edges_line[node.parent.repr_col + 1:]

        return edges_line

    def _get_vertical_char(self, node):
        if not node.parent:
            return LINE_VERTICAL

        if len(node.parent.children) == 1:
            return LINE_VERT_ONLY
        elif node == node.parent.children[0]:
            return LINE_VERT_LEFTMOST
        elif node == node.parent.children[-1]:
            return LINE_VERT_RIGHTMOST

        return LINE_VERTICAL

    def get_children_breadth_first(self):
        visited = []
        queue = [self]

        while queue:
            node = queue.pop(0)
            if node not in visited:
                visited.append(node)
                queue.extend(node.children)

        return visited

    def get_string_width(self):
        children_width = sum([c.get_string_width() for c in self.children])

        return max(len(repr(self.content)), children_width) + len(PADDING) * 2


def find_expansion(lhs: NonTerminal, next_token, expansions) -> Union[bool, str, Expansion]:
    for expansion in expansions[lhs]:
        if expansion.rhs is None:
            return "ε"

        if isinstance(expansion.rhs[0], Terminal) and expansion.rhs[0].token.name == next_token.name:
            return expansion

        if isinstance(expansion.rhs[0], NonTerminal) and find_expansion(expansion.rhs[0], next_token, expansions):
            return expansion

    return False


def parse_file(filename, expansions):
    with open(filename, "r") as f:
        s = f.read()

    return parse_string(s, expansions)


def parse_string(str_to_parse, expansions):
    return syntax_analyse(lex(str_to_parse), expansions)


def syntax_analyse(tokens: List[Token], expansions: Dict[NonTerminal, List[Expansion]]):
    root = ParseTreeNode(NonTerminal("p"))
    root.parse_tokens(tokens, expansions)

    return root
