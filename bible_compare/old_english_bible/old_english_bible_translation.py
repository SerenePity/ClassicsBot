import john
import luke
import mark
import matthew


def get_old_english(book, chapter, verse):
    if book.lower() == 'john':
        return john[chapter][verse]
    if book.lower() == 'luke':
        return luke[chapter][verse]
    if book.lower() == 'mark':
        return mark[chapter][verse]
    if book.lower() == 'matthew':
        return matthew[chapter][verse]
