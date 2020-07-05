import argparse
import logging
from pathlib import Path

from .render import render_sprite

logger = logging.getLogger("poke_sprite")

parser = argparse.ArgumentParser()
parser.add_argument("path", type=str)
parser.add_argument("--debug", action="store_true")
parser.add_argument("--seek", type=int, default=0)
parser.add_argument("--size", type=str, default=None)


def main(args):
    path = Path(args.path)
    seek = args.seek

    if args.size:
        width, height = map(int, args.size.split(","))
        size = (width, height)
    else:
        size = None

    logger.info("Reading sprite from %s", path)
    if seek:
        logger.info("Will start reading from offset 0x%x", seek)

    with open(path, "rb") as sprite:
        sprite.seek(seek)
        render_sprite(sprite, show=True, pokedex_size=size)


if __name__ == '__main__':
    _args = parser.parse_args()
    _level = "DEBUG" if _args.debug else "INFO"
    logging.basicConfig(level=_level, format="%(message)s")
    main(_args)
