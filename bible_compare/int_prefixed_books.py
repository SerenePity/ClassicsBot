import re

int_prefix_books = {'1 samuel', '2 samuel', '1 kings', '2 kings', '1 chronicles', '2 chronicles', '1 corinthians',
                    '2 corinthians', '1 thessalonians', '2 thessalonians', '1 timothy', '2 timothy', '1 peter',
                    '2 peter', '1 john', '2 john', '3 john'}

int_prefix_books_regex = f'({"|".join(int_prefix_books)})'
int_books_regex = re.compile(int_prefix_books_regex)


def get_int_prefix_book(s):
    matches = re.search(int_books_regex, s)
    return matches.group(0) if matches else None
