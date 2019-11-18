from typing import Dict, List

from lexer import Token
from parseerror import ParseError
from syntaxanalyser import ParseTreeNode
from typechecker import _type_check


class Scope:
    def __init__(self):
        self.vars: Dict[str, ScopeEntry] = {}

    def __repr__(self):
        return "{" + ",".join([repr(v) for v in self.vars.values()]) + "}"

    def declare(self, node: ParseTreeNode):
        assert(node.is_terminal("ID"))

        identifier = node.get_terminal_attribute()
        token = node.content.token
        if identifier in self.vars:
            raise ParseError(f"Redefinition of identifier {identifier}",
                             token.line_num, token.col_num, token.context_line)
        else:
            self.vars[identifier] = ScopeEntry(token)

    def assign(self, id_node: ParseTreeNode, value_node: ParseTreeNode):
        assert(id_node.is_terminal("ID"))

        identifier = id_node.get_terminal_attribute()

        # check that the id has been declared in scope
        self.use_var(id_node)

        self.vars[identifier].assign(id_node, value_node)

    def use_var(self, id_node: ParseTreeNode):
        identifier = id_node.get_terminal_attribute()
        token = id_node.content.token
        if identifier not in self.vars or not self.vars[identifier].has_been_declared(token):
            raise ParseError(f"Use of undeclared identifier {identifier}",
                             token.line_num, token.col_num, token.context_line)

    def get_var_type(self, id_node: ParseTreeNode, procedures):
        identifier = id_node.get_terminal_attribute()
        return self.vars[identifier].get_type_at_node(id_node, procedures)


class ScopeEntry:
    def __init__(self, declare_token: Token):
        self.declare_token = declare_token
        self.assignments: List[Dict[str, ParseTreeNode]] = []

    def __repr__(self):
        return self.declare_token.attribute

    def has_been_declared(self, token):
        return _is_before_or_at(self.declare_token, token)

    def assign(self, id_node: ParseTreeNode, value_node: ParseTreeNode):
        self.assignments.append({"id_node": id_node, "value_node": value_node})

    def get_type_at_node(self, node, procedures):
        token = node.content.token
        latest_type = None
        for assignment in self.assignments:
            id_node = assignment["id_node"]
            if _is_before_or_at(id_node.content.token, token):
                # if this is a self assignment, then do not type check or infer type from this
                # to avoid infinite recursion
                # self assignment eg "x := x + 1"
                parent = id_node.get_common_parent(node)
                if parent.is_non_terminal("a"):
                    continue

                # we sometimes need to type check the value node
                # because type checking happens left to right, and assignments are right to left
                # eg x := 1, we should type check 1 and set x's type to its type
                value_node = assignment["value_node"]
                if not hasattr(value_node, "type"):
                    _type_check(value_node, procedures)
                latest_type = value_node.type

        if not latest_type \
                and not token.line_num == self.declare_token.line_num and token.col_num == self.declare_token.col_num:
            raise ParseError(f"Variable never assigned to {token}",
                             token.line_num, token.col_num, token.context_line)

        return latest_type


def semantic_analyse(root: ParseTreeNode):
    assert root.is_non_terminal("p")  # this must be program root

    global_scope = Scope()
    root.scope = global_scope

    for child in root.children:
        child.scope = global_scope

        if child.is_non_terminal("compound"):
            _analyse(child, global_scope)  # begin the semantic analyse proper once we find the actual program body


def _analyse(node: ParseTreeNode, scope):
    node.scope = scope

    if node.is_non_terminal("function_definition"):
        _analyse_func_definition(node)

    elif node.is_non_terminal("v"):  # variable declaration, with optional assignment
        _analyse_variable_assignment(node, scope, is_declaration=True)

    elif node.is_non_terminal("a"):  # assignment of an already declared variable
        _analyse_variable_assignment(node, scope, is_declaration=False)

    elif node.is_non_terminal("pr") and node.has_child("GET"):  # assign declared variable to user input
        _analyse_variable_assignment(node, scope, is_declaration=False)

    elif node.is_terminal("ID"):
        scope.use_var(node)

    elif node.children:
        for child in node.children:
            _analyse(child, scope)


def _analyse_variable_assignment(node, scope, is_declaration):
    id_node = None
    assign_node = None
    for child in node.children:
        child.scope = scope

        if child.is_terminal("ID"):
            id_node = child
            if is_declaration:
                scope.declare(id_node)

        # for 'v' and 'a' non-terminals, respectively
        elif child.is_non_terminal("var_assign") or child.is_non_terminal("expression") or child.is_terminal("GET"):
            assign_node = child

    assert id_node is not None and (assign_node is not None or is_declaration)
    if assign_node is not None:
        scope.assign(id_node, assign_node)
        _analyse(assign_node, scope)


def _analyse_func_definition(node):
    scope = Scope()  # each function has its own scope
    for child in node.children:
        child.scope = scope

        if child.is_non_terminal("func_def_args"):
            _analyse_func_args(child, scope)
        elif child.is_non_terminal("function_compound"):
            _analyse(child, scope)


def _analyse_func_args(node, scope):
    type_node = node.get_child("arg_type")
    type_node.children[0].scope = scope

    for child in node.children:
        child.scope = scope

        if child.is_terminal("ID"):
            scope.declare(child)
            assert type_node
            scope.assign(child, type_node)  # fix the type of the variable
        elif child.is_non_terminal("later_func_def_arg"):
            _analyse_func_args(child, scope)


# returns true iff a appears before or at the same location as b
def _is_before_or_at(a: Token, b: Token):
    return a.line_num < b.line_num or (a.line_num == b.line_num and a.col_num <= b.col_num)


# returns true iff a appears strictly before b
def _is_before(a: Token, b: Token):
    return a.line_num < b.line_num or (a.line_num == b.line_num and a.col_num < b.col_num)
