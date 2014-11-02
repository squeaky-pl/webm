from __future__ import print_function

from struct import unpack
from datetime import datetime, timedelta
from functools import partial


def read_packed_uint(read, msb):
    first_byte = ord(read(1))
    head = not msb

    if first_byte & 0b10000000:
        return first_byte ^ (head * 0b10000000)
    elif first_byte & 0b01000000:
        return unpack('>H', chr((head * 0b01000000) ^ first_byte) + read(1))[0]
    elif first_byte & 0b00100000:
        return unpack('>L', '\0' + chr((head * 0b00100000) ^ first_byte) + read(2))[0]
    elif first_byte & 0b00010000:
        return unpack('>L', chr((head * 0b00010000) ^ first_byte) + read(3))[0]
    elif first_byte & 0b00001000:
        return unpack('>Q', '\0\0\0' + chr((head * 0b00001000) ^ first_byte) + read(4))[0]
    elif first_byte & 0b00000100:
        return unpack('>Q', '\0\0' + chr((head * 0b00000100) ^ first_byte) + read(5))[0]
    elif first_byte & 0b00000010:
        return unpack('>Q', '\0' + chr((head * 0b00000010) ^ first_byte) + read(6))[0]
    elif first_byte & 0b00000001:
        return unpack('>Q', chr(head * 0b00000001) + read(7))[0]


def read_id(read):
    return read_packed_uint(read, True)


def read_size(read):
    return read_packed_uint(read, False)



def read_int(read, size):
    data = read(size)

    if size == 1:
        return ord(data)
    elif size == 2:
        return unpack('>H', data)[0]
    elif size == 3:
        return unpack('>L', '\0' + data)[0]
    elif size == 4:
        return unpack('>L', data)[0]


ref_datetime = datetime(2001, 1, 1)


def read_date(read, size=None):
    data = read(8)
    microseconds = unpack('>q', data)[0] / 1000

    return ref_datetime + timedelta(microseconds=microseconds)


def read_float(read, size):
    data = read(size)[::-1]

    if size == 4:
        return unpack('@f', data)[0]


def read_string(read, size):
    return read(size)


def read_element_header(read):
    return read_id(read), read_size(read)


readers = {
    'INT': read_int,
    'UINT': read_int,
    'FLOAT': read_float,
    'STR': read_string,
    'UTF8': read_string,
    'DATE': read_date,
    'BIN': read_string
}

ebml = {
    0x1a45dfa3: ('ebml', 'MASTER'),
    0x4286: ('version', 'UINT'),
    0x42f7: ('read_version', 'UINT'),
    0x42f2: ('max_id_length', 'UINT'),
    0x4282: ('doctype', 'STR'),
    0x42f3: ('max_size_length', 'UINT'),
    0x4287: ('doctype_version', 'UINT'),
    0x4285: ('doctype_read_version', 'UINT'),
    0xec: ('void', 'BIN')
}

matroska = {
    0x18538067: ('segment', 'MASTER'),
    0x114d9b74: ('seek_head', 'MASTER'),
    0x4dbb: ('seek', 'MASTER'),
    0x1549a966: ('info', 'MASTER'),
    0x1654ae6b: ('tracks', 'MASTER'),
    0xae: ('track_entry', 'MASTER'),
    0xe0: ('video', 'MASTER'),
    0xb0: ('width', 'UINT'),
    0xba: ('height', 'UINT'),
    0xe1: ('audio', 'MASTER'),
    0xb5: ('sampling_frequency', 'FLOAT'),
    0x1c53bb6b: ('cues', 'MASTER'),
    0xbb: ('cue_point', 'MASTER'),
    0xb7: ('cue_track_points', 'MASTER'),
    0x1f43b675: ('cluster', 'MASTER'),
    0xa3: ('simple_block', 'BIN')
}


def parse_element(spec, read):
    eid, size = read_element_header(read)
    try:
        name, typ = spec[eid]
    except KeyError:
        name, typ = 'unknown_' + format(eid, 'x'), None

    try:
        reader = readers[typ]
    except KeyError:
        reader = read_string

    return name, size, typ, partial(reader, read, size)


def dump_tree(tell, parse_element):
    stack = []

    while 1:
        name, size, typ, reader = parse_element()

        print('  ' * len(stack) + name + ' ' + str(size) + ' ', end='')

        if typ == 'MASTER':
            stack.append(tell() + size)
            print()
            continue
        elif typ in ('STR', 'UTF8', 'BIN', None):
            if size < 48:
                print(repr(reader()), end='')
            else:
                reader()
                print('...', end='')
        else:
            print(repr(reader()), end='')

        print()

        pos = tell()

        stack = [s for s in stack if pos < s]


def dump_file(filename):
    with open(filename, 'rb') as f:
        spec = ebml.copy()
        spec.update(matroska)

        dump_tree(f.tell, partial(parse_element, spec, f.read))


if __name__ == '__main__':
    import sys

    dump_file(sys.argv[1])
