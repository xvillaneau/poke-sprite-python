import logging

from PIL import Image, ImageOps

from .compression import decompress_sprite

logger = logging.getLogger("poke_sprite")


def render_sprite(bytes_stream, *, show=False, pokedex_size=None):
    """
    Main sprite rendering routine. Given a byte stream corresponding to
    the compressed sprite, will decompress it and transform it into a
    2-bit deep image, similar to what the Game Boy could process.
    """
    # Run the sprite decompression. This populates the buffer so that
    # regions B and C hold the low and high bit planes respectively.
    buffer, width, height = decompress_sprite(bytes_stream)

    # In practice, the size of a sprite is stored in the Pokédex and is
    # supplied to the padding algorithm. For convenience, we'll allow
    # the size from the compressed sprite (which may not match the one
    # in the Pokédex) to be used by default.
    if pokedex_size is not None:
        width, height = pokedex_size

    # Now that the size may have changed, check that our buffer is
    # still large enough and allocate more space if it isn't. This
    # only applies for glitch Pokémon sprites.
    buffer_size_tiles = 49 * 2 + max(49, width * height)
    to_allocate = len(buffer) - buffer_size_tiles * 8
    if to_allocate > 0:
        buffer.extend(bytearray(to_allocate))

    # The buffer regions can each hold a full sprite bit plane of 7×7
    # tiles (49×49 pixels, or 392 bytes). We call them A, B, and C.
    buffer_a = memoryview(buffer)
    buffer_b = buffer_a[392:]
    buffer_c = buffer_a[784:]

    # Position adjustment copies the tiles between buffers so that they
    # are in the correct position in the 7×7 display.
    logger.info(
        "Adjusting the position of the sprite for a size of %dx%d",
        width, height
    )
    adjust_position(width, height, buffer_b, buffer_a)  # B -> A
    adjust_position(width, height, buffer_c, buffer_b)  # C -> B

    # Combine the data in A and B to form the 2-bit sprite bitmap
    zip_bit_planes(buffer)

    logger.info("Processing complete")
    if show:
        im = Image.frombuffer("L", (56, 56), render_8bit(buffer[392:1176]))
        ImageOps.invert(im).show()

    return bytes(buffer[392:1176])


def adjust_position(width, height, src_buffer, dest_buffer):
    """
    Copy the tiles of a sprite between buffers so that their new
    position is correct.
    """
    # Calculate the position of the upper-left corner of the sprite
    # in the 7×7 grid. This places it center-bottom.
    h_pad = (7 - height)
    w_pad = (8 - width) // 2
    offset = 7 * w_pad + h_pad

    # Emulate the 8-bit overflow when calculating the bytes offset,
    # which causes the signature appearance of MissingNo.
    src, dst = 0, (offset * 8) % 256

    # Clear the destination buffer with zeros
    for i in range(392):
        dest_buffer[i] = 0

    h_col = height * 8
    # For each column, copy the data into its new position.
    # The source pointer moves linearly across the data, while the
    # destination pointer skips tiles to fix their position.
    for _ in range(width):
        dest_buffer[dst:dst + h_col] = src_buffer[src:src + h_col]
        src += h_col
        dst += 56


def zip_bit_planes(buffer):
    """
    Combine the bit planes in regions A & B into the full 2-bit sprite.
    This data is built so that each pair of bytes corresponds to the
    low and high bits (respectively) of a row of 8 pixels
    """
    # Start 3 pointers at the end of A, B, and C
    pt_a, pt_b, pt_zip = 391, 783, 1175

    # Go through the buffer backwards, alternating low and high bits
    while pt_zip >= 392:
        buffer[pt_zip] = buffer[pt_b]
        buffer[pt_zip - 1] = buffer[pt_a]
        pt_zip -= 2
        pt_a -= 1
        pt_b -= 1


ZIPPED_NIBBLES = [
    0x00000000, 0x00000001, 0x00000100, 0x00000101,
    0x00010000, 0x00010001, 0x00010100, 0x00010101,
    0x01000000, 0x01000001, 0x01000100, 0x01000101,
    0x01010000, 0x01010001, 0x01010100, 0x01010101,
]


def render_8bit(sprite_2bit):
    """
    Convert the column-order 2-bit deep Game Boy sprite into a 8-bit
    bitmap in row order, for display on a modern device.

    The 2-bit image data is organized in an unusual way:
    - Each pair of bytes encodes one row of 8 pixels in a tile. The
      first byte holds the low bits, and the second the high bits.
    - Tiles are ordered in column order, then left to right.

    So converting to a bitmap requires three transformations:
    1. Transpose the offset from column-order to row order
    2. Zip the two bytes so that their bits alternate
    3. Convert 2-bit depth (0-3) into 8-bit (0-255)
    """
    screen = bytearray(49 * 64)

    # Iterate over the pairs of bytes in the 2-bit image
    for pt in range(0, 784, 2):

        # Compute the location of the 8-pixel row in the new image
        col, row = divmod(pt, 112)
        pos = row * 28 + col * 8

        # Zip the bytes: nibbles of 4 bits is converted into 4 bytes,
        # then the upper and lower nibbles of each bytes are combined.
        a, b = sprite_2bit[pt:pt + 2]
        upper = ZIPPED_NIBBLES[a >> 4] + (ZIPPED_NIBBLES[b >> 4] << 1)
        lower = ZIPPED_NIBBLES[a & 15] + (ZIPPED_NIBBLES[b & 15] << 1)
        zipped = (upper << 32) + lower

        # Scale the value of those 8 bytes to 0-255, and write them
        zipped *= 85
        screen[pos:pos+8] = zipped.to_bytes(8, "big")

    return screen
