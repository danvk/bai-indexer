#!/usr/bin/env python
"""Print out start:stop locations for each reference in a BAI file.

Usage:
    bai_indexer.py /path/to/file.bam.bai > /path/to/file.bam.bai.json
"""

import json
import struct
import sys

# -- helper functions for reading binary data from a stream --

def _unpack(stream, fmt):
    size = struct.calcsize(fmt)
    buf = stream.read(size)
    return struct.unpack(fmt, buf)[0]


def _read_int32(stream):
    return _unpack(stream, '<i')


def _read_uint32(stream):
    return _unpack(stream, '<I')


def _read_uint64(stream):
    return _unpack(stream, '<Q')


class InvalidBaiFileError(Exception):
    pass


def extract_offsets(data_stream):
    """Generate an index of a BAM Index (BAI) file.

    Args:
        data_stream: A stream of bytes from the BAI file, as returned
            by open().  Anything with .read() and .tell() methods will do.

    Returns:
        A dict with information about the BAM and BAI files. For example:

        {'minBlockIndex': 1234,
         'chunks': [[8, 123456], [123456, 234567], ...]}

        The chunks are [start, stop) byte ranges in the BAI file for each
        ref. minBlockIndex is the position of the first block in the BAM
        file.

    Raises:
        InvalidBaiFileError: if the bytes do not comprise a valid BAI file.
    """
    magic = data_stream.read(4)
    if magic != 'BAI\x01':
        raise InvalidBaiFileError('This is not a BAI file (missing magic)')

    minBlockIndex = 1000000000
    refs = []
    n_ref = _read_int32(data_stream)
    for i in range(0, n_ref):
        ref_start = data_stream.tell()
        n_bin = _read_int32(data_stream)
        for j in range(0, n_bin):
            bin_id = _read_uint32(data_stream)
            n_chunk = _read_int32(data_stream)

            chunks = []
            for k in range(0, n_chunk):
                chunk_beg = _read_uint64(data_stream)
                chunk_end = _read_uint64(data_stream)

        n_intv = _read_int32(data_stream)
        intvs = []
        for j in range(0, n_intv):
            ioffset = _read_uint64(data_stream)
            if ioffset:
                # This mirrors dalliance's calculation, but I don't trust it.
                bi = ioffset / 65536
                if ioffset % 65536 != 0:
                    bi += 65536
                minBlockIndex = min(minBlockIndex, bi)
        ref_end = data_stream.tell()

        refs.append((ref_start, ref_end))

    # Undocumented field: # of unmapped reads
    # See https://github.com/samtools/hts-specs/pull/2/files
    try:
        num_unmapped = _read_uint64(data_stream)
    except struct.error:
        pass

    extra_bytes = data_stream.read()
    if extra_bytes != '':
        raise InvalidBaiFileError(
                'Extra data after expected EOF (%d bytes)' % len(extra_bytes))

    return {
        'minBlockIndex': minBlockIndex,
        'chunks': refs
    }


if __name__ == '__main__':
    data = open(sys.argv[1], 'rb')
    out = extract_offsets(data)
    print json.dumps(out)
