from PIL import Image, ImageOps
from .bitwise import BitStreamReader


def decompress_sprite(bytes_stream, show=False):
    bits = BitStreamReader(bytes_stream)
    read = bits.read

    buffer_a = bytearray(392)
    buffer_b = bytearray(392)
    buffer_c = bytearray(392)

    width = read(4)
    height = read(4)
    # Bits to read per sprite plane

    if read(1):
        buffer_0, buffer_1 = buffer_c, buffer_b
    else:
        buffer_0, buffer_1 = buffer_b, buffer_c

    _decompress_rle(bits, width, height, buffer_0)

    mode = read(1)
    if mode:
        mode += read(1)

    _decompress_rle(bits, width, height, buffer_1)

    if mode != 1:
        delta_decode_buffer(width, height, buffer_1)
    delta_decode_buffer(width, height, buffer_0)
    if mode != 0:
        for i in range(width * height * 8):
            buffer_1[i] ^= buffer_0[i]

    adjust_position(width, height, buffer_b, buffer_a)
    adjust_position(width, height, buffer_c, buffer_b)

    if show:
        im = Image.frombuffer("L", (56, 56), render(buffer_a, buffer_b))
        ImageOps.invert(im).show()


def _decompress_rle(bit_stream, width, height, buffer):
    # Constant we'll use a lot
    h_col = height * 8
    # Keeps track of where to write the next pair of bytes
    pos, shift = 0, 6
    # Number of pairs to write
    size = width * height * 32
    # Number of pairs written
    written = 0

    # First bit tells whether we start by data or RLE
    read = bit_stream.read
    mode = read(1)

    while written < size:
        if mode == 1:  # data
            if pair := read(2):
                buffer[pos] |= (pair << shift)
                written += 1
            else:  # data terminated; switch mode and don't write
                mode = 0
                continue

        else:  # Decode RLE
            n_bits = 1
            while read(1):  # Detect sequence of 1..10
                n_bits += 1
            rle_count = (1 << n_bits) + read(n_bits) - 1
            # Those are all pairs of zero, no need to write each
            mode = 1
            written += rle_count

        # Compute where in the buffer to write next
        col = written // h_col
        pos = written % h_col + (col // 4) * h_col
        shift = 6 - 2 * (col % 4)


def delta_decode_buffer(width, height, buffer):
    # Delta decoding is done by row, but data in the buffer is by
    # columns of bytes from top to bottom. So we'll need to query
    # a bit all around the place.

    row, col, state = 0, 0, 0
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


DELTA_DECODE_NIBBLE = [
    0b0000, 0b0001, 0b0011, 0b0010,  # 0000, 0001, 0010, 0011
    0b0111, 0b0110, 0b0100, 0b0101,  # 0100, 0101, 0110, 0111
    0b1111, 0b1110, 0b1100, 0b1101,  # 1000, 1001, 1010, 1011
    0b1000, 0b1001, 0b1011, 0b1010,  # 1100, 1101, 1110, 1111
]


def adjust_position(width, height, src_buffer, dest_buffer):
    h_pad = 7 - height
    w_pad = (8 - width) // 2
    h_col = height * 8

    for i in range(392):
        dest_buffer[i] = 0

    src, dst = 0, w_pad * 56 + h_pad * 8
    for _ in range(width):
        dest_buffer[dst:dst + h_col] = src_buffer[src:src + h_col]
        src += h_col
        dst += 56


def render(buffer_0, buffer_1):
    screen = bytearray(49 * 64)
    for pointer in range(49 * 8):
        col, row = divmod(pointer, 56)
        pos = row * 56 + col * 8

        a, b = buffer_0[pointer], buffer_1[pointer]
        for i in range(8):
            f = 1 << (7 - i)
            screen[pos + i] = (a & f > 0) * 85 + (b & f > 0) * 170
    return screen
