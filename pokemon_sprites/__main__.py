import argparse
from pathlib import Path

from .poke_rle import read_sprite

parser = argparse.ArgumentParser()
parser.add_argument("path", type=str)
parser.add_argument("--seek", type=int, default=0)
parser.add_argument("--size", type=str, default=None)


def main(args):
    path = Path(args.path)

    if args.size:
        width, height = map(int, args.size.split(","))
        size = (width, height)
    else:
        size = None

    with open(path, "rb") as sprite:
        if args.seek:
            sprite.seek(args.seek)
        read_sprite(sprite, show=True, declared_size=size)


if __name__ == '__main__':
    main(parser.parse_args())
