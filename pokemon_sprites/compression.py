import logging

from .bitwise import BitStreamReader

logger = logging.getLogger("poke_sprite")


def decompress_sprite(bytes_stream, declared_size=None):
    bits = BitStreamReader(bytes_stream)
    read = bits.read

    width = bits.read(4)
    height = bits.read(4)
    # Bits to read per sprite plane
    logger.debug("Detected a size of %d×%d tiles from the binary data", width, height)

    max_size_tiles = max(width * height, 49)
    if declared_size is not None:
        declared_w, declared_h = declared_size
        max_size_tiles = max(max_size_tiles, declared_w * declared_h)

    buffer = bytearray(392 * 2 + 8 * max_size_tiles)
    logger.debug("Created memory buffer of %d bytes", len(buffer))
    view = memoryview(buffer)
    buffer_b = view[392:]
    buffer_c = view[392 * 2:]

    if invert_buffers := read(1):
        buffer_0, buffer_1 = buffer_c, buffer_b
    else:
        buffer_0, buffer_1 = buffer_b, buffer_c
    logger.debug("Bit plane order detected: BP0 in %s", 'C' if invert_buffers else 'B')

    logger.debug("Decompressing Bit Plane 0")
    decompress_to_buffer(bits, width, height, buffer_0)

    mode = read(1)
    if mode:
        mode += read(1)
    mode += 1

    logger.debug("Decompressing Bit Plane 1")
    decompress_to_buffer(bits, width, height, buffer_1)

    logger.debug("Decoding mode %d detected", mode)
    if mode == 1:
        delta_decode_buffer(width, height, buffer_1)
        delta_decode_buffer(width, height, buffer_0)

    elif mode == 2:
        delta_decode_buffer(width, height, buffer_0)
        xor_buffers(width, height, buffer_1, buffer_0)

    elif mode == 3:
        delta_decode_buffer(width, height, buffer_1)
        delta_decode_buffer(width, height, buffer_0)
        xor_buffers(width, height, buffer_1, buffer_0)

    logger.info("Decompression complete")
    return buffer, width, height


def decompress_to_buffer(bit_stream, width, height, buffer):
    # Constant we'll use a lot
    h_col = height * 8
    # Number of bytes to write
    size = width * h_col
    # Keeps track of where to write the next pair of bytes
    pos, shift = 0, 6

    for pair in decompress_stream(bit_stream):
        buffer[pos] |= (pair << shift)
        pos += 1

        if pos % h_col == 0:
            if shift == 0 and pos >= size:
                break
            if shift > 0:
                shift -= 2
                pos -= h_col
            else:
                shift = 6


def decompress_stream(bit_stream):
    # First bit tells whether we start by data or RLE
    read = bit_stream.read
    mode = read(1)

    while True:
        if mode == 1:  # data
            while pair := read(2):
                yield pair
            mode = 0

        else:  # Decode RLE
            n_bits = 1
            while read(1):  # Detect sequence of 1..10
                n_bits += 1
            rle_count = (1 << n_bits) + read(n_bits) - 1
            # Those are all pairs of zeros
            for _ in range(rle_count):
                yield 0
            mode = 1


def delta_decode_buffer(width, height, buffer):
    # Delta decoding is done by row, but data in the buffer is by
    # columns of bytes from top to bottom. So we'll need to query
    # a bit all around the place.

    row, col, state = 0, 0, 0
    logger.debug("Applying Delta decoding")
    while row < (height * 8):
        pos = col * height * 8 + row
        byte = buffer[pos]

        first = DELTA_DECODE_NIBBLE[byte >> 4] ^ (0b1111 * state)
        state = first & 1
        second = DELTA_DECODE_NIBBLE[byte & 0b1111] ^ (0b1111 * state)
        state = second & 1

        buffer[pos] = (first << 4) + second
        col += 1

        if col >= width:
            row += 1
            col, state = 0, 0


def xor_buffers(width, height, write_buffer, read_buffer):
    for i in range(width * height * 8):
        write_buffer[i] ^= read_buffer[i]


DELTA_DECODE_NIBBLE = [
    0b0000, 0b0001, 0b0011, 0b0010,  # 0000, 0001, 0010, 0011
    0b0111, 0b0110, 0b0100, 0b0101,  # 0100, 0101, 0110, 0111
    0b1111, 0b1110, 0b1100, 0b1101,  # 1000, 1001, 1010, 1011
    0b1000, 0b1001, 0b1011, 0b1010,  # 1100, 1101, 1110, 1111
]
