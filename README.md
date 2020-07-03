# Pokémon Sprite Codec

This is a project for fun based on the [Pokémon Sprite Decompression Explained]
video by the _Retro Games Mechanics Explained_ YouTube channel. The goal is to
reproduce the image compression and decompression algorithm used in the
Pokémon Blue (which I played), Red and Yellow games for the Nintendo Gameboy.

Progress: Still a Proof-of-Concept

Core functions:
- [x] Implement bitwise stream reader
- [x] Implement basic functional decompression
- [ ] Implement delta / XOR decoding based on the mode
- [ ] Implement final image output from the two bit planes

Maybe someday:
- [ ] Clean up, test, and document
- [ ] Implement 7 x 7 buffer with the correct tiles position
- [ ] Correctly implement the full continuous memory buffer
- [ ] Attempt to reproduce the `MISSINGNO.` sprite glitch
- [ ] Implement compression

### Acknowledgments

Practically 100% of what I'm attempting to reproduce has been researched and
explained by Alex "Dotsarecool" Losego. They have also made [a far better
interactive online tool][rgme-decompress] for playing around with the
compression algorithm of the game.

### License

Copyright ©2020 Xavier Villaneau,
distributed under the Mozilla Public License 2.0

Pokémon is a registered trademark of Nintendo.

[Pokémon Sprite Decompression Explained]: https://youtu.be/aF1Yw_wu2cM
[rgme-decompress]: http://www.dotsarecool.com/rgme/tech/gen1decompress.html