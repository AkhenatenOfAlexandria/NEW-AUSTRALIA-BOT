import discord
import json
import re


def BIBLE(MESSAGE):
    
    MESSAGE = MESSAGE.upper()
    PATTERN = r'(?P<BOOK>[\dA-Z\s]+) (?P<CHAPTER>\d+):(?P<VERSE>\d+)'
    
    MATCH = re.match(PATTERN, MESSAGE)

    if MATCH:
        BOOK = MATCH.group('BOOK').strip()
        CHAPTER = MATCH.group('CHAPTER').strip()
        VERSE = MATCH.group('VERSE').strip()
    else:
        raise KeyError("Unknown reference.")
    BOOK = BOOK[0:4]
    if BOOK in ("GOSP", "1 AL", "2 AL", "3 AL", "4 AL"):
        PATH = f"BIBLE/ORTHODOXY_BIBLE/{BOOK}.JSON"
        try:
            with open(PATH, 'r', encoding='utf-8') as file:
                book = json.load(file)
            if CHAPTER in book and VERSE in book[CHAPTER]:
                NAME = book["NAME"]

                EMBED = discord.Embed(
                    colour = discord.Colour.red(),
                    title = f"{NAME} {CHAPTER} - Alabastian Orthodoxy Bible (AOB)",
                    description = f"{VERSE} {book[CHAPTER][VERSE]}"
                )
                return EMBED
            else:
                raise KeyError("Verse not found!")
        except FileNotFoundError:
            raise KeyError("Verse not found!")
    else:
        raise KeyError("Book not found!")

