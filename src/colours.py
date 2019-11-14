import sys

RED = "\033[91m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
RESET_COLOUR = "\033[0m"


if not sys.stdout.isatty():
    # stdout is redirected - disable colours so files aren't clogged up with ugly colour codes
    RED = BLUE = YELLOW = RESET_COLOUR = ""
