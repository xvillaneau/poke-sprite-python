from io import BytesIO


class BitStreamReader:
    """
    Bit-wise binary stream reader. Given a bytes stream, this tool can
    iterate over its individual bits.

    This makes the sprite decompression a lot easier.
    """
    CHUNK_SIZE = 4

    def __init__(self, bytes_stream: BytesIO):
        self._pointer = 0
        self._buffer = 0
        self._eof = False
        self._stream = bytes_stream

    def read(self, n=8):
        """
        Read the next n bits from the stream, 8 by default.
        """
        out = 0

        while n > 0:
            if self._pointer == 0:
                # We've run out of bits in the buffer; query the next
                # chunk of bytes from the stream.
                chunk = self._stream.read(self.CHUNK_SIZE)
                if not chunk:
                    self._eof = True
                    break
                self._buffer = int.from_bytes(chunk, "big")
                self._pointer = 8 * len(chunk)

            # We can only read as many bits have we have left in the
            # buffer. If more bits were required than we have available
            # then the process is repeated as many times as required.
            n_read = min(n, self._pointer)

            # Prepare read mask. Example: to read 3 bits with 5 bits
            # left in the buffer, the mask will be 0b11100
            shift = self._pointer - n_read
            mask = ((1 << n_read) - 1) << shift

            # Make room for the bits then write them
            out <<= n_read
            out += (self._buffer & mask) >> shift

            # Update our pointer and counters
            self._pointer -= n_read
            n -= n_read

        return out
