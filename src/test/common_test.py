import os


def get_data_dir():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "data")


def get_grammar_file():
    return os.path.join(get_data_dir(), "..", "oreo.grammar")
