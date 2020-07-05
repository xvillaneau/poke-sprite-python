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
    buffer, width, height = decompress_sprite(bytes_stream, pokedex_size)

    # The buffer regions can each hold a full sprite bit plane of 7×7
    # tiles (49×49 pixels, or 392 bytes). We call them A, B, and C.
    buffer_a = memoryview(buffer)
    buffer_b = buffer_a[392:]
    buffer_c = buffer_a[784:]

    # In practice, the size of a sprite is stored in the Pokédex and is
    # supplied to the padding algorithm. For convenience, we'll allow
    # the size from the compressed sprite (which may not match the one
    # in the Pokédex) to be used by default.
    if pokedex_size is not None:
        width, height = pokedex_size

    # Position adjustment copies the tiles between buffers so that they
    # are in the correct position in the 7×7 display.
    logger.info(
        "Adjusting the position of the sprite for a size of %dx%d",
        width, height
    )
    adjust_position(width, height, buffer_b, buffer_a)  # B -> A
    adjust_position(width, height, buffer_c, buffer_b)  # C -> B

    logger.info("Processing complete")
    if show:
        im = Image.frombuffer("L", (56, 56), render(buffer_a, buffer_b))
        ImageOps.invert(im).show()


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
