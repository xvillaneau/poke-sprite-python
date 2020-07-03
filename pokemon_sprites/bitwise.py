from io import BytesIO


class BitStreamReader:
    __slots__ = ("_pointer", "_buffer", "_stream", "_eof")

    def __init__(self, bytes_stream: BytesIO):
        self._pointer = 0
        self._buffer = 0
        self._eof = False
        self._stream = bytes_stream

    def __iter__(self):
        return self

    def __next__(self):
        if self._eof:
            raise StopIteration
        return self.read(1)

    def read(self, n=8):
        out = 0

        while n > 0:
            if self._pointer == 0:
                byte = self._stream.read(1)
                if not byte:
                    self._eof = True
                    break
                self._buffer = ord(byte)
                self._pointer = 8

            # TODO: Optimize by reading chunk of buffer at once
            out <<= 1
            out += (self._buffer & 128) >> 7
            self._buffer <<= 1
            self._pointer -= 1
            n -= 1

        return out
