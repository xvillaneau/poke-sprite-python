from pathlib import Path
import sys

from .poke_rle import decompress_sprite

path = Path(sys.argv[1])

with open(path, "rb") as sprite:
    decompress_sprite(sprite, show=True)
