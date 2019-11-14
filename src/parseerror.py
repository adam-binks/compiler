from colours import RED, BLUE, YELLOW, RESET_COLOUR


class ParseError(Exception):
    def __init__(self, message, line_num, col_num, context_line, is_lex_error=False):
        self.line_num = line_num
        self.col_num = col_num

        context_line = self.highlight_error_token(col_num, context_line)

        err_type = "Lex error" if is_lex_error else "Parse error"
        formatted_message = f"{RED}{err_type} on line {YELLOW}{line_num}:{col_num}{RED}: {message}{RESET_COLOUR}\n"
        formatted_message += context_line + "\n"

        formatted_message = self.add_arrow_pointing_to_error_token(col_num, context_line, formatted_message)

        self.message = formatted_message
        super().__init__(formatted_message)

    def highlight_error_token(self, col_num, context_line):
        try:
            next_space = col_num + context_line[col_num:].index(' ')
        except ValueError:
            next_space = len(context_line)
        context_line = context_line[0:max(col_num - 1, 0)] + RED + context_line[col_num - 1:next_space] + RESET_COLOUR \
                       + context_line[next_space:]
        return context_line

    def add_arrow_pointing_to_error_token(self, col_num, context_line, formatted_message):
        num_tabs = context_line[0:col_num].count("\t")
        num_non_tabs = max(col_num - num_tabs - 1, 0)
        formatted_message += ("\t" * num_tabs) + (" " * num_non_tabs) + f"{BLUE}↑{RESET_COLOUR}"
        return formatted_message
