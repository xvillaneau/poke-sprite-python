from pathlib import Path
import sys

from .poke_rle import read_sprite

path = Path(sys.argv[1])

with open(path, "rb") as sprite:
    read_sprite(sprite, show=True)
