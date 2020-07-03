from PIL import Image, ImageShow
from .bitwise import BitStreamReader


def decompress_sprite(bytes_stream, show=False):
    bits = BitStreamReader(bytes_stream)
    read = bits.read

    buffer_b = bytearray(392)
    buffer_c = bytearray(392)

    width = read(4)
    height = read(4)
    # Bits to read per sprite plane
    size = width * height * 64

    if read(1):
        buffer_0, buffer_1 = buffer_c, buffer_b
    else:
        buffer_0, buffer_1 = buffer_b, buffer_c

    _decompress_rle(bits, size, buffer_0)

    mode = read(1)
    if mode:
        mode += read(1)

    _decompress_rle(bits, size, buffer_1)

    if mode != 1:
        delta_decode_buffer(buffer_1)
    delta_decode_buffer(buffer_0)
    if mode != 0:
        buffer_1 ^= buffer_0

    if show:
        im = Image.frombytes("1", (56, 56), bytes(buffer_0))
        ImageShow.show(im)


def _decompress_rle(bit_stream, size, buffer):
    read = bit_stream.read

    packet = read(1)
    pos, shift = 0, 6
    written = 0

    while written < size:
        if packet == 1:  # data
            if pair := read(2):
                buffer[pos] |= (pair << shift)
                written += 2
            else:  # data terminated; switch mode and don't write
                packet = 0
                continue

        else:  # Decode RLE
            n_bits = 1
            while read(1):  # Detect sequence of 1..10
                n_bits += 1
            rle_count = (1 << n_bits) + read(n_bits) - 1
            # Those are all pairs of zero, no need to write each
            written += rle_count * 2
            packet = 1

        col = written // 112
        row = (written >> 1) % 56
        pos = 7 * row + (col // 4)
        shift = 6 - 2 * (col % 4)


def delta_decode_buffer(buffer):
    row, col, state = 0, 0, 0
    while row < 56:
        byte = buffer[row * 7 + col]

        first = DELTA_DECODE_NIBBLE[byte >> 4] ^ (0b1111 * state)
        state = first & 1
        second = DELTA_DECODE_NIBBLE[byte & 0b1111] ^ (0b1111 * state)
        state = second & 1

        buffer[row * 7 + col] = (first << 4) + second
        col += 1

        if col >= 7:
            row += 1
            col, state = 0, 0


DELTA_DECODE_NIBBLE = [
    0b0000, 0b0001, 0b0011, 0b0010,  # 0000, 0001, 0010, 0011
    0b0111, 0b0110, 0b0100, 0b0101,  # 0100, 0101, 0110, 0111
    0b1111, 0b1110, 0b1100, 0b1101,  # 1000, 1001, 1010, 1011
    0b1000, 0b1001, 0b1011, 0b1010,  # 1100, 1101, 1110, 1111
]