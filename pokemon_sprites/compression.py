from .bitwise import BitStreamReader


def decompress_sprite(bytes_stream):
    bits = BitStreamReader(bytes_stream)
    read = bits.read

    buffer_b = bytearray(392)
    buffer_c = bytearray(392)

    width = bits.read(4)
    height = bits.read(4)
    # Bits to read per sprite plane

    invert_buffers = bool(read(1))
    if invert_buffers:
        buffer_0, buffer_1 = buffer_c, buffer_b
    else:
        buffer_0, buffer_1 = buffer_b, buffer_c

    decompress_to_buffer(bits, width, height, buffer_0)

    mode = read(1)
    if mode:
        mode += read(1)
    mode += 1

    decompress_to_buffer(bits, width, height, buffer_1)

    return buffer_b, buffer_c, width, height, mode, invert_buffers


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
