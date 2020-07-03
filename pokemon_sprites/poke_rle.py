from .bitwise import BitStreamReader


def decompress_sprite(bytes_stream):
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
    pass

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
