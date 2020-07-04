from PIL import Image, ImageOps

from .compression import decompress_sprite


def read_sprite(bytes_stream, show=False):

    buffer, width, height = decompress_sprite(bytes_stream)

    buffer_a = memoryview(buffer)
    buffer_b = buffer_a[392:]
    buffer_c = buffer_a[784:]

    adjust_position(width, height, buffer_b, buffer_a)
    adjust_position(width, height, buffer_c, buffer_b)

    if show:
        im = Image.frombuffer("L", (56, 56), render(buffer_a, buffer_b))
        ImageOps.invert(im).show()


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
