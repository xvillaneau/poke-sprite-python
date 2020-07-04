from PIL import Image, ImageOps

from .compression import decompress_sprite


def read_sprite(bytes_stream, show=False):

    buffer_b, buffer_c, width, height, mode, invert_buffers = decompress_sprite(bytes_stream)
    buffer_a = bytearray(392)

    if invert_buffers:
        buffer_0, buffer_1 = buffer_c, buffer_b
    else:
        buffer_0, buffer_1 = buffer_b, buffer_c

    if mode != 2:
        delta_decode_buffer(width, height, buffer_1)
    delta_decode_buffer(width, height, buffer_0)
    if mode != 1:
        for i in range(width * height * 8):
            buffer_1[i] ^= buffer_0[i]

    adjust_position(width, height, buffer_b, buffer_a)
    adjust_position(width, height, buffer_c, buffer_b)

    if show:
        im = Image.frombuffer("L", (56, 56), render(buffer_a, buffer_b))
        ImageOps.invert(im).show()


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
