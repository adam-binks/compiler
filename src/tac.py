from typing import Union, List

from syntaxanalyser import ParseTreeNode

IF_FALSE_GOTO = "IfFalseGoto"

# TAC doesn't have booleans
TRUE_TAC = 1
FALSE_TAC = 0

# maps from oreo operators to TAC operators
# or if no oreo operator exists, just maps from the TAC operator to itself
binary_ops = {
    "+": "+",
    "-": "-",
    "*": "*",
    "/": "/",
    "==": "==",
    "<": "<",
    "AND": "&&",
    "OR": "||"
}
unary_ops = {
    "NOT": "not",
    "Goto": "Goto",
    IF_FALSE_GOTO: IF_FALSE_GOTO
}

COMBINER_OPERATORS = ["+", "-", "/", "*", "AND", "OR", "relative_operator", "simple_expr"]
COMBINERS = ["and_or_b", "mul_div", "add_sub", "comp_e"]
COMBINER_OPERANDS = ["bool", "term", "factor", "TRUE", "FALSE", "simple_expr", "compare_expr", "expression"]


class TacProgram:
    def __init__(self, parse_tree: ParseTreeNode):
        Label.auto_increment = 0
        TacVariable.auto_increment = 0

        self.program: List[Union[Label, TacInstruction]] = []
        self.variables: List[TacVariable] = []
        self.oreo_to_tac(parse_tree)

    def __repr__(self):
        return "\n".join([self.instruction_str(i) for i in self.program])

    # pretty print with tabs
    def instruction_str(self, instruction):
        if isinstance(instruction, Label):
            return repr(instruction) + ":"
        else:
            return f"\t{instruction}"

    # return an unused, unique variable name
    def _new_variable(self):
        var = TacVariable()
        self.variables.append(var)

        return var

    # appends instructions and labels to self.program
    # also adds a result property to the node
    def oreo_to_tac(self, node: ParseTreeNode):
        if hasattr(node, "result"):
            return  # this node has already been processed, no need to do it again

        if node.is_non_terminal("p"):
            # ignore the top level program declaration, just process the program compound itself
            self.oreo_to_tac(node.get_child("compound"))
            return

        # if statements and while loops are carefully compiled in order, so the right things are in the right labels
        elif node.is_non_terminal("i"):
            self._compile_if_statement(node)
            return

        elif node.is_non_terminal("w"):
            self._compile_while_statement(node)
            return

        for child in node.children:
            self.oreo_to_tac(child)

        if node.is_terminal("NUMBER") or node.is_terminal("STRING"):
            literal = node.content.token.attribute
            if node.is_terminal("NUMBER"):
                literal = int(literal)
            node.result = NodeResult(literal=literal)

        elif node.is_terminal("TRUE") or node.is_terminal("FALSE"):
            bool_literal = TRUE_TAC if node.is_terminal("TRUE") else FALSE_TAC
            node.result = NodeResult(literal=bool_literal)

        elif node.is_terminal("ID"):
            node.result = NodeResult(variable=self._get_variable(node.content.token.attribute, create=True))

        elif node.is_in(["term", "factor", "simple_expr", "compare_expr", "bool"]):
            node.result = self._compile_optional_combiner(node)

        elif node.is_non_terminal("expression"):
            node.result = self._compile_optional_combiner(node, specific_combiners=["and_or_b"])

        elif node.is_non_terminal("a"):
            self._compile_assignment(node.get_child("ID"), node.get_child("expression"))

        elif node.is_non_terminal("v") and node.has_child("var_assign"):
            self._compile_assignment(node.get_child("ID"), node.get_child("var_assign").get_child("expression"))

        if hasattr(node, "result"):
            assert isinstance(node.result, NodeResult)
        else:
            node.result = "NULL RESULT"  # to prevent reprocessing processed nodes which do not have a result

    def _compile_print_expression(self, node: ParseTreeNode):
        if node.has_child("GET"):
            return self._add_instruction(
                op=""
            )

    def _compile_while_statement(self, node: ParseTreeNode):
        while_start_label = Label("while_start")
        end_while_label = Label("while_end")

        self.program.append(while_start_label)

        condition_node = node.get_child("bool")
        self.oreo_to_tac(condition_node)

        # if the condition doesn't hold, leave the loop
        # IfZ a Goto L1;
        # > result=L1 op=IfFalseGoto, arg1=a
        self._add_instruction(
            arg1=condition_node.result,
            op=IF_FALSE_GOTO,
            result=end_while_label
        )

        # the condition held, so execute the loop body
        self.oreo_to_tac(node.get_child("compound"))

        # go back to start of loop
        self._add_goto_instruction(while_start_label)

        self.program.append(end_while_label)

    def _compile_if_statement(self, node: ParseTreeNode):
        condition_node = node.get_child("bool")
        self.oreo_to_tac(condition_node)

        condition_is_false_label = Label('if_false')

        # IfZ a Goto L1;
        # > result=L1 op=IfFalseGoto, arg1=a
        self._add_instruction(
            arg1=condition_node.result,
            op=IF_FALSE_GOTO,
            result=condition_is_false_label
        )

        # the if statement was true
        self.oreo_to_tac(node.get_child("compound"))

        if node.has_child("optional_else"):
            end_of_else_block_label = Label('else_end')

            # if condition held, skip the else block
            self._add_goto_instruction(end_of_else_block_label)

            # the else block
            self.program.append(condition_is_false_label)
            self.oreo_to_tac(node.get_child("optional_else"))
            self.program.append(end_of_else_block_label)

        else:
            # there's no else block: if condition doesn't hold, just jump down here
            self.program.append(condition_is_false_label)

    def _add_goto_instruction(self, label):
        self._add_instruction(
            op="Goto",
            result=label
        )

    def _compile_assignment(self, id_node, assign_node):
        id_variable_name = id_node.content.token.attribute

        # the assign node is probably to the right of the id_node, so we need to compile it first so that the id_node
        # can look at its result
        self.oreo_to_tac(assign_node)

        if assign_node.result.is_literal() or assign_node.result.variable.is_named:
            # we actually need to perform a copy operation
            # because either:
            # (i) if assign_node is a variable, then:
            # the assign_node's variable value could change later, but this id's value should not change
            # with it, if it does
            # (ii) if assign_node is a literal, then there is no variable holding it, so we definitely need it

            # if a variable for this id exists, use it
            # otherwise create a new one
            id_variable = TacVariable(id_variable_name)
            return self._add_instruction(
                result=id_variable,
                op="copy",
                arg1=assign_node.result.get()
            )

        else:
            assert assign_node.result.is_variable() and not assign_node.result.variable.is_named
            # in this case, we can just update the unnamed temporary variable to be this named variable!
            # and therefore don't need to spend a cycle copying the value  8)
            assign_node.result.variable.set_name(id_variable_name)

    def _get_variable(self, name, create=False):
        try:
            return next(v for v in self.variables if v.is_named and v.name == name)
        except StopIteration:
            if create:
                return TacVariable(name)
            else:
                raise ValueError(f"Variable {name} does not exist")

    # these various nodes have uniform parse tree structure: ["term", "factor", "simple_expr"]
    # they can thus all be dealt with in the same way
    # they either add code to combine, if they have an operator (eg +)
    # or else, they just inherit the result from their child that has it
    def _compile_optional_combiner(self, node, specific_combiners=None):
        combiners = COMBINERS if specific_combiners is None else specific_combiners

        if node.has_child("ID_PAREN"):  # for factor
            raise NotImplementedError

        elif node.has_child("NOT"):  # for bool
            return self._add_instruction(op="NOT", arg1=node.get_child("bool").result)

        else:
            combiner = node.get_a_child(combiners, optional=True)
            if combiner:
                left_operand = node.get_a_child(COMBINER_OPERANDS).result

                # if the combiner has a child which is a combiner too:
                # 1) generate the code for the child combiner
                # 2) use the child combiner's output as the right operand, and generate the code for this combiner
                # otherwise, just use the term/factor that is a child of this node (ie a sibling of the combiner)
                combiner_child = combiner.get_a_child(COMBINERS, optional=True)
                if combiner_child:
                    right_operand = self._compile_optional_combiner(combiner)
                else:
                    right_operand = combiner.get_a_child(COMBINER_OPERANDS).result

                return self._compile_combiner(left_operand, right_operand, combiner)

            else:
                inherit_node_result(node,
                                    ["NUMBER", "STRING", "ID", "TRUE", "FALSE", "simple_expr"] + COMBINER_OPERANDS)
                return node.result

    # combiner_node can be mul_div, add_sub or and_or_b, as these operations are all dealt with uniformly
    def _compile_combiner(self, left_operand, right_operand, combiner_node):
        relative_operator = combiner_node.get_child("relative_operator", optional=True)
        if relative_operator:
            return self._compile_rel_op(left_operand, right_operand, relative_operator.content.token.name)

        return self._add_instruction(
            arg1=left_operand,
            arg2=right_operand,
            op=combiner_node.get_a_child(COMBINER_OPERATORS).content.token.name
        )

    def _compile_rel_op(self, left_operand, right_operand, relop):
        assert relop in ["<", ">", "==", "<=", ">="]

        if relop in ["<", "=="]:
            # these are in TAC so just add a single instruction
            return self._add_instruction(
                op=relop,
                arg1=left_operand,
                arg2=right_operand
            )

        if relop == ">":
            # FLIP the order of the operators and make it a "<"
            return self._add_instruction(
                op="<",
                arg1=right_operand,
                arg2=left_operand
            )

        if relop in ["<=", ">="]:
            # return, eg, "a < b OR a == b"
            strict_relop = relop[0]  # "<" or ">"
            strict_truth = self._compile_rel_op(left_operand, right_operand, strict_relop)
            equality = self._compile_rel_op(left_operand, right_operand, "==")
            return self._add_instruction(
                arg1=strict_truth,
                op="OR",
                arg2=equality
            )

    def _add_instruction(self, result=None, op=None, arg1=None, arg2=None):
        if isinstance(arg1, NodeResult):
            arg1 = arg1.get()
        if isinstance(arg2, NodeResult):
            arg2 = arg2.get()

        if result is None:
            result = self._new_variable()
        self.program.append(TacInstruction(
            result=result,
            op=op,
            arg1=arg1,
            arg2=arg2
        ))

        return NodeResult(variable=result)


class NodeResult:
    def __init__(self, literal=None, variable=None):
        assert literal is not None or variable is not None and not (literal is not None and variable is not None)
        self.literal = literal  # str(literal) if (literal is not None) else None
        self.variable = variable

    def __repr__(self):
        return self.get()

    def is_literal(self):
        return self.literal is not None

    def is_variable(self):
        return self.variable is not None

    def get(self):
        if self.is_literal():
            if isinstance(self.literal, str):
                return f'"{self.literal}"'
            else:
                return str(self.literal)
        if self.is_variable():
            return self.variable


class Label:
    auto_increment = 0

    def __init__(self, tag):
        Label.auto_increment += 1
        self.name = f"L{str(Label.auto_increment)}_{tag}"

    def __repr__(self):
        return self.name


class TacVariable:
    auto_increment = 0

    def __init__(self, name=None):
        if name is not None:
            self.name = name
            self.is_named = True
        else:
            self.is_named = False
            TacVariable.auto_increment += 1
            self.name = str(TacVariable.auto_increment)

    def set_name(self, new_name):
        self.name = new_name
        self.is_named = True

    # prepend all user variable names with v_ to prevent possible conflict with auto-generated ones, which
    # have a prefix of t_
    def __repr__(self):
        prefix = "v_" if self.is_named else "t_"
        return prefix + self.name


class TacInstruction:
    # Examples:
    # a = b + c;
    # > result=a, op=+, arg1=b, arg2=c
    # IfZ a Goto L1;
    # > result=L1 op=IfFalseGoto, arg1=a
    # a = b
    # > result=a, op=copy arg1=b
    # Goto L1;
    # > result=L1 op=Goto
    def __init__(self, result, op=None, arg1=None, arg2=None):
        assert all(o is None or isinstance(o, str) or isinstance(o, TacVariable) or isinstance(o, Label)
                   for o in [result, arg1, arg2])
        assert op is not None

        self.result = result
        self.arg1 = arg1
        self.arg2 = arg2
        self.op = self.get_tac_op(op)

    def __repr__(self):
        if self.op == "copy":
            return f"{self.result} = {self.arg1};"

        if self.op == IF_FALSE_GOTO:
            return f"IfZ {self.arg1} Goto {self.result};"

        if self.op == "Goto":
            return f"Goto {self.result};"

        if self.op in unary_ops.values():
            return f"{self.result} = {self.op} {self.arg1};"

        if self.op in binary_ops.values():
            return f"{self.result} = {self.arg1} {self.op} {self.arg2};"

        raise ValueError(f"Cannot __repr__ this TAC instruction")

    def get_tac_op(self, oreo_op):
        if oreo_op == "Goto":
            return oreo_op

        if oreo_op == "copy":
            assert self.arg2 is None
            return "copy"

        if oreo_op in binary_ops.keys():
            assert self.arg1 is not None and self.arg2 is not None
            return binary_ops[oreo_op]

        if oreo_op in unary_ops.keys():
            assert self.arg1 is not None and self.arg2 is None
            return unary_ops[oreo_op]

        raise ValueError(f"Unrecognised operator {oreo_op}")


# parse_tree should have been semantically analysed and type checked
def compile_to_tac(parse_tree: ParseTreeNode):
    return TacProgram(parse_tree)


def inherit_node_result(node: ParseTreeNode, child_names: List[str]):
    child = node.get_a_child(child_names)
    node.result = child.result
