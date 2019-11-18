from typing import List

from parseerror import ParseError
from syntaxanalyser import ParseTreeNode, Terminal

# types
BOOL = "BOOL"
NUM = "NUM"
STR = "STR"
NONE = "NONE"  # for functions that return nothing


# publicly callable top level type check
def type_check(root: ParseTreeNode):
    # do not type check the name of the program, just the body
    _type_check(root.get_child("compound"), [])


# private recursive call of type checker
def _type_check(node: ParseTreeNode, procedures: List[ParseTreeNode]):
    # only type check each node once
    # this is useful because sometimes type checking happens out of order, eg in assignment
    if hasattr(node, "type"):
        return

    # do this first to allow recursive procedures
    if node.is_non_terminal("function_definition"):
        procedures.append(node)

    # type check from the bottom up
    for child in node.children:
        _type_check(child, procedures)

    # there is no nice way to do this because many cases have unique behaviour
    # so sadly the best simple way to do it is a big old branching if statement
    if node.is_non_terminal("function_definition"):
        node.type = node.get_child("function_compound").type

    elif node.is_non_terminal("function_compound"):
        _type_check_function_compound(node)

    elif node.is_non_terminal("return_statement"):
        _type_check_return_statement(node)

    elif node.is_non_terminal("arg_type"):
        node.type = node.children[0].type

    elif node.is_non_terminal("expression"):
        _type_check_expression(node)

    elif node.is_non_terminal("compare_expr"):
        _type_check_compare_expr(node)

    elif node.is_non_terminal("simple_expr"):
        _type_check_simple_expr(node)

    elif node.is_non_terminal("term"):
        _type_check_term(node)

    elif node.is_non_terminal("factor"):
        _type_check_factor(node, procedures)

    elif node.is_non_terminal("bool"):
        _type_check_bool(node)

    elif node.is_non_terminal("var_assign"):
        node.type = node.get_child("expression").type

    elif node.is_non_terminal("comp_e"):
        _require_child_type(node, "expression", NUM)
        node.type = BOOL

    elif node.is_non_terminal("add_sub"):
        _require_child_type(node, "term", NUM)
        node.type = NUM

    elif node.is_non_terminal("mul_div"):
        _require_child_type(node, "factor", NUM)
        node.type = NUM

    elif node.is_terminal("ID"):
        var_type = node.scope.get_var_type(node, procedures)
        node.type = var_type

    elif node.is_terminal("NUMBER") or node.is_terminal("NUM"):
        node.type = NUM

    elif node.is_terminal("TRUE") or node.is_terminal("FALSE") or node.is_terminal("BOOL"):
        node.type = BOOL

    # GET gets a string from the user
    elif node.is_terminal("STRING") or node.is_terminal("STR") or node.is_terminal("GET"):
        node.type = STR


def _type_check_return_statement(node):
    optional_expr_node = node.get_child("optional_expr", optional=True)
    if optional_expr_node:
        node.type = optional_expr_node.children[0].type
    else:
        node.type = NONE


def _type_check_function_compound(node):
    node.type = NONE

    for child in node.children:
        return_node = child.get_child("return_statement", optional=True)
        if return_node:
            node.type = return_node.type


def _type_check_bool(node):
    if node.has_child("relative_operator"):
        _require_child_type(node, "simple_expr", NUM)
        _require_child_type(node, "expression", NUM)
    elif node.has_child("expression"):
        _require_child_type(node, "expression", BOOL)
    node.type = BOOL


def _type_check_term(node):
    if node.has_child("mul_div"):
        _require_child_type(node, "factor", NUM)
        node.type = NUM
    else:
        node.type = node.get_child("factor").type


def _type_check_simple_expr(node):
    if node.has_child("add_sub"):
        _require_child_type(node, "term", NUM)
        node.type = NUM
    else:
        node.type = node.get_child("term").type


def _type_check_compare_expr(node):
    if node.has_child("comp_e"):
        _require_child_type(node, "simple_expr", NUM)
        node.type = BOOL
    else:
        node.type = node.get_child("simple_expr").type


def _type_check_expression(node):
    if node.has_child("and_or_b"):
        _require_child_type(node, "compare_expr", BOOL)
        node.type = BOOL
    else:
        node.type = node.get_child("compare_expr").type


def _type_check_factor(node, procedures):
    if len(node.children) == 1:
        node.type = node.children[0].type
    elif node.has_a_child(["TRUE", "FALSE", "NOT"]):
        node.type = BOOL
    elif node.has_child("expression"):
        node.type = node.get_child("expression").type
    elif node.has_child("ID_PAREN"):
        _type_check_function_call(node, procedures, none_return_allowed=False)
    else:
        raise ValueError(f"Programming error: type checking factor {node}")


def _type_check_function_call(node: ParseTreeNode, procedures, none_return_allowed):
    id_paren = node.get_child("ID_PAREN")
    called_procedure = id_paren.content.token.attribute

    for procedure in procedures:
        if procedure.get_child("ID_PAREN").content.token.attribute == called_procedure:
            if procedure.type == NONE and not none_return_allowed:
                token = id_paren.content.token
                raise ParseError(f"Can't assign to procedure that returns none",
                                 token.line_num, token.col_num, token.context_line)

            node.type = procedure.type
            return

    token = id_paren.content.token
    raise ParseError(f"Call to undeclared procedure",
                     token.line_num, token.col_num, token.context_line)


def _require_child_type(node: ParseTreeNode, child: str, required_type):
    _require_type(node.get_child(child), required_type)


def _require_type(node, required_type):
    if node.type != required_type:
        child = node
        while not isinstance(child.content, Terminal):
            child = child.children[0]
        token = child.content.token
        raise ParseError(f"{node} at {token} has type {node.type}, should be {required_type}",
                         token.line_num, token.col_num, token.context_line)
