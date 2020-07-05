import logging

from .bitwise import BitStreamReader

logger = logging.getLogger("poke_sprite")


def decompress_sprite(bytes_stream, declared_size=None):
    bits = BitStreamReader(bytes_stream)
    read = bits.read

    # The first byte describes the dimensions of the data to decode, in
    # tiles. This size may not match that declared in the Pokédex.
    width = read(4)
    height = read(4)
    logger.debug("Detected a size of %d×%d tiles from the binary data", width, height)

    # The Game Boy RAM is such that the routine can write anywhere it
    # wants to, sometimes with hilarious results. We don't really want
    # to emulate that entirely, but we need at least enough memory for
    # the entire sprite to be decompressed.

    # Normally the buffer holds three 7×7 bit planes so that will be
    # our minimum size. If we are dealing with a glitched sprite of
    # much larger size, we also allocate enough memory so that the C
    # region can hold all of it.

    max_size_tiles = max(width * height, 49)
    if declared_size is not None:
        declared_w, declared_h = declared_size
        max_size_tiles = max(max_size_tiles, declared_w * declared_h)

    buffer = bytearray(392 * 2 + 8 * max_size_tiles)
    logger.debug("Created memory buffer of %d bytes", len(buffer))

    # Buffers B and C are abstracted as views from a given offset.
    # Note that going too far in B overflows into C!
    view = memoryview(buffer)
    buffer_b = view[392:]
    buffer_c = view[784:]

    # We will be writing two bit planes in memory and this next bit
    # tells us which goes where. Plane 0 is the first one in the data
    # and plane 1 the second, and either can be written to B or C.
    if invert_buffers := read(1):
        buffer_0, buffer_1 = buffer_c, buffer_b
    else:
        buffer_0, buffer_1 = buffer_b, buffer_c
    logger.debug("Bit plane order detected: BP0 in %s", 'C' if invert_buffers else 'B')

    # Decompress the first bit plane
    logger.debug("Decompressing Bit Plane 0")
    decompress_to_buffer(bits, width, height, buffer_0)

    # Between the two planes, the decoding mode is one of three codes:
    # 0, 10, or 11 for modes 1, 2 and 3 respectively.
    mode = read(1)
    if mode == 1:
        mode += read(1)
    mode += 1

    # Decompress the second bit plane
    logger.debug("Decompressing Bit Plane 1")
    decompress_to_buffer(bits, width, height, buffer_1)
    logger.debug("Total bits read: %d", bits.counter)

    # Apply the decoding steps based on the mode
    logger.debug("Decoding mode %d detected", mode)
    # Modes 1 & 3: Delta-decode bit plane 1
    if mode != 2:
        delta_decode_buffer(width, height, buffer_1)
    # Any mode: Delta-decode bit plane 0
    delta_decode_buffer(width, height, buffer_0)
    # Modes 2 & 3: XOR bit plane 1 in-place with bit plane 0
    if mode != 1:
        xor_buffers(width, height, buffer_1, buffer_0)

    logger.info("Decompression complete")
    return buffer, width, height


def decompress_to_buffer(bit_stream, width, height, buffer):
    """
    Decompression routine for a single bit plane. Will read the given
    Bit stream and write the decompressed data in the buffer.
    """
    # This routine does not do the actual decompression; its job is to
    # write the decompressed data to the correct place in memory. It
    # also keeps track of the progress and stops once the required
    # amount of data has been written.

    # The decompressed data is a stream of pairs along 2-bit wide
    # columns in the image, top to bottom then left to right. The data
    # in memory is also in columns in the same order, but 8-bit wide.

    start_count = bit_stream.counter
    h_col = height * 8  # Constant we'll use a lot
    size = width * h_col  # Number of bytes to write

    pos = 0  # Offset of the byte in memory to write to
    shift = 6  # Position in that byte to write the pair at

    for pair in _decompress_stream(bit_stream):
        # Write the pair to the byte, but only the 1s. If there
        # already was data in the buffer, it will overlap.
        buffer[pos] |= (pair << shift)
        pos += 1

        if pos % h_col == 0:
            # If we've reached the end of a column:
            if shift == 0 and pos >= size:
                # If we're at the last position, stop
                break
            if shift > 0:
                # If we are not in the rightmost column of pairs in the
                # current column of bytes, go back to the top so that
                # we can write the next pairs.
                shift -= 2
                pos -= h_col
            else:
                # Otherwise, move on to the next column of tiles.
                shift = 6

    logger.debug(
        "Done decompressing bit plane (%d bits -> %d bits)",
        bit_stream.counter - start_count, pos * 8
    )


def _decompress_stream(bit_stream):
    """
    Core decompression routine. Given a stream of bits, will blindly
    apply the RLE decompression as long as it is asked to. This is a
    generator that yields pairs of bytes (ints between 0 and 3).

    The compression in Pokémon is such that long chains of zeros are
    efficiently encoded. The data is stored as alternating data and
    Run-Length Encoding packages; the first store any pairs with 1s
    uncompressed, the second efficiently counts pairs of 00s.
    """
    read = bit_stream.read

    def decode_data():
        """
        Decode uncompressed data.

        Read every pair of bits as-is until we read 00.
        """
        while pair := read(2):
            yield pair

    def decode_rle():
        """
        Decode Run-Length Encoded data.

        This packet represents a sequence of 00 pairs. It is made of
        two parts: first is a string of 1s followed by one 0, and its
        length tells us how many bits long the second part is.
        The value encoded is the sum of the two parts plus one.

        Examples (dot emphasized split between parts):
        - 1110.0101  -> 14 + 5 + 1 = 20
        - 110.111    -> 6 + 7 + 1 = 14
        - 10.00      -> 2 + 0 + 1 = 3
        - 0.0        -> 0 + 0 + 1 = 1
        """
        # Start by detecting the first sequence
        n_bits = 1
        while read(1):
            n_bits += 1
        # 1..10 that's N long is equal to (1 << N) - 2
        rle_count = (1 << n_bits) + read(n_bits) - 1
        # Those are all pairs of zeros
        for _ in range(rle_count):
            yield 0

    # First bit indicates whether the start is RLE or data.
    if read(1):
        yield from decode_data()

    # After that, alternate RLE and data until we're done
    while True:
        yield from decode_rle()
        yield from decode_data()


DELTA_DECODE_NIBBLE = [
    # Delta-decoded sequences of 4 bits, with zero as initial state
    0b0000, 0b0001, 0b0011, 0b0010,  # From 0000, 0001, 0010, 0011
    0b0111, 0b0110, 0b0100, 0b0101,  # From 0100, 0101, 0110, 0111
    0b1111, 0b1110, 0b1100, 0b1101,  # From 1000, 1001, 1010, 1011
    0b1000, 0b1001, 0b1011, 0b1010,  # From 1100, 1101, 1110, 1111
]


def delta_decode_buffer(width, height, buffer):
    """
    Reverse the delta-encoding operation on a bit plane

    The delta-encoding is done so that identical consecutive bits are
    encoded as 0s, and changes encoded as 1s. For example, the byte
    00110111 is encoded as 00101100 (if the initial state was 0).

    In this particular cases, a few important details apply:
    - The encoding is applied row by row in the image as per the
      declared dimensions in the data, which generally does not
      correspond to a continuous region of memory.
    - At the start of each row, the state is reset to zero.
    """
    logger.debug("Applying Delta decoding")

    # Scan the image row by row, then column by column
    for row in range(height * 8):
        state = 0
        for col in range(width):
            # Calculate the position in memory to read
            pos = col * height * 8 + row
            byte = buffer[pos]

            # Decoding a byte is done by decoding its halves (nibbles)
            # separately using a lookup table. If the state was 1, then
            # the result is inverted. The last bit is the new state.
            first = DELTA_DECODE_NIBBLE[byte >> 4] ^ (0b1111 * state)
            state = first & 1
            second = DELTA_DECODE_NIBBLE[byte & 0b1111] ^ (0b1111 * state)
            state = second & 1

            # Combine nibbles to make the decoded byte, and write it
            buffer[pos] = (first << 4) + second


def xor_buffers(width, height, write_buffer, read_buffer):
    """
    Combine one buffer region with another using "Exclusive OR".
    The first buffer is modified in-place using the second.
    """
    for i in range(width * height * 8):
        write_buffer[i] ^= read_buffer[i]
