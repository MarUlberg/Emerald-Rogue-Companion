#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project: Emerald Rogue Companion
Module: emerald_rogue_companion.py
Author: Martinius Ulberg
Contact: MarUlberg@gmail.com
License: MIT License
Description:
    Inspect Pokémon Emerald Rogue save data and report save info, quest
    completion, Pokédex status, berry-plot growth, and berry/Pokéblock data.
"""

import sys
import struct
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from pathlib import Path

# ============================================================
# Save data and Pokémon metadata
# ============================================================

# Calibrated to the v2.0.1a-EX BPS/save profile.
SECTOR_SIZE = 4096
SECTOR_DATA_SIZE = 4084
NUM_SECTORS = 32
POKEMON_STORAGE_SECTOR_START = 5
POKEMON_STORAGE_SECTOR_COUNT = 9
BAG_ITEMS_OFFSET = 0x578
BAG_ITEM_SLOT_COUNT = 450
SAVEBLOCK2_PLAY_TIME_OFFSET = 0x0E
SAVEBLOCK2_PLAYER_NAME_OFFSET = 0x00
SAVEBLOCK1_MONEY_OFFSET = 0x4A8
SAVEBLOCK1_LOCATION_OFFSET = 0x04
SAVEBLOCK2_HUB_NAME_OFFSET = 0xEE4
HUB_NAME_LENGTH = 16
# Every hub save seen so far is in map group 2; needs more testing.
HUB_MAP_GROUP = 2
HUB_SNAPSHOT_MONEY_OFFSET = 0x7899
PLAYER_NAME_LENGTH = 8

# Rogue save and quest-state data in the v2.0.x EX Pokémon Storage stream.
ROGUE_SAVE_BLOCK_OFFSET = 0x5DC4
ROGUE_DIFFICULTY_CONFIG_OFFSET = 0x6D26
ROGUE_SAVE_SECRET_ID = 27615
QUEST_STATE_SIZE = 8
QUEST_COMPLETED_MASK = 1 << 5
QUEST_DIFFICULTY_SHIFT = 16
QUEST_DIFFICULTIES = ("Easy", "Average", "Hard", "Brutal")
DIFFICULTY_PRESETS = ("Easy", "Average", "Hard", "Brutal", "Custom")
DIFFICULTY_TOGGLE_BYTE_COUNT = 3
DIFFICULTY_RANGE_PRESET_INDEX = 6
DIFFICULTY_PRESET_REQUIREMENTS = (
    {},
    {5: False, 7: False, 8: True},
    {1: False, 2: False, 5: False, 7: False, 8: True},
    {1: False, 2: False, 4: True, 5: False, 6: True, 7: False, 8: True},
)

# SaveBlock1 layout inside the reconstructed 4-sector block.
DEX_SEEN_OFFSET = 0x30B4
DEX_SIZE = 191
DEX_CAUGHT_OFFSET = DEX_SEEN_OFFSET + DEX_SIZE

# Display the complete National Pokédex through Generation IX.
NUM_POKEMON = 1024
POKEMON_GENERATIONS = (
    ("Kanto", 1, 152, "Gen1.png", 6),
    ("Johto", 152, 252, "Gen2.png", 249),
    ("Hoenn", 252, 387, "Gen3.png", 383),
    ("Sinnoh", 387, 494, "Gen4.png", 483),
    ("Unova", 494, 650, "Gen5.png", 644),
    ("Kalos", 650, 722, "Gen6.png", 717),
    ("Alola", 722, 810, "Gen7.png", 791),
    ("Galar", 810, 906, "Gen8.png", 888),
    ("Paldea", 906, 1026, "Gen9.png", 1007),
)
POKEMON_GENERATION_SHEETS = tuple(
    (generation[1], generation[2], generation[3])
    for generation in POKEMON_GENERATIONS
)
POKEMON_SPRITE_SIZE = 32
POKEMON_SPRITES_PER_ROW = 12
STATUS_SPRITE_NAMES = ("Undiscovered", "Seen", "Caught", "Shiny")
STATUS_SPRITE_SIZE = 12
# Total width in pixels of the Pokédex list; the name column absorbs any change.
DEX_TABLE_WIDTH = 170
# Width in pixels of the Pokédex and Quest Book scrollbars.
SCROLLBAR_WIDTH = 8
# Form species in the EX build shift internal IDs for the Generation IX base species.
GEN9_SPECIES_ID_OFFSETS = (
    (906, 383),
    (917, 384),
    (926, 385),
    (932, 388),
    (965, 389),
    (979, 391),
    (983, 392),
    (1000, 393),
    (1009, 397),
    (1013, 398),
    (1014, 399),
    (1018, 407),
)

# National Dex names keyed by Pokédex number.
# We keep them embedded so the script works offline and without downloads.

POKEMON_NAMES = {
    1: 'Bulbasaur', 2: 'Ivysaur', 3: 'Venusaur', 4: 'Charmander', 5: 'Charmeleon', 6: 'Charizard',
    7: 'Squirtle', 8: 'Wartortle', 9: 'Blastoise', 10: 'Caterpie', 11: 'Metapod', 12: 'Butterfree',
    13: 'Weedle', 14: 'Kakuna', 15: 'Beedrill', 16: 'Pidgey', 17: 'Pidgeotto', 18: 'Pidgeot',
    19: 'Rattata', 20: 'Raticate', 21: 'Spearow', 22: 'Fearow', 23: 'Ekans', 24: 'Arbok',
    25: 'Pikachu', 26: 'Raichu', 27: 'Sandshrew', 28: 'Sandslash', 29: 'Nidoran', 30: 'Nidorina',
    31: 'Nidoqueen', 32: 'Nidoran♂', 33: 'Nidorino', 34: 'Nidoking', 35: 'Clefairy', 36: 'Clefable',
    37: 'Vulpix', 38: 'Ninetales', 39: 'Jigglypuff', 40: 'Wigglytuff', 41: 'Zubat', 42: 'Golbat',
    43: 'Oddish', 44: 'Gloom', 45: 'Vileplume', 46: 'Paras', 47: 'Parasect', 48: 'Venonat',
    49: 'Venomoth', 50: 'Diglett', 51: 'Dugtrio', 52: 'Meowth', 53: 'Persian', 54: 'Psyduck',
    55: 'Golduck', 56: 'Mankey', 57: 'Primeape', 58: 'Growlithe', 59: 'Arcanine', 60: 'Poliwag',
    61: 'Poliwhirl', 62: 'Poliwrath', 63: 'Abra', 64: 'Kadabra', 65: 'Alakazam', 66: 'Machop',
    67: 'Machoke', 68: 'Machamp', 69: 'Bellsprout', 70: 'Weepinbell', 71: 'Victreebel',
    72: 'Tentacool', 73: 'Tentacruel', 74: 'Geodude', 75: 'Graveler', 76: 'Golem', 77: 'Ponyta',
    78: 'Rapidash', 79: 'Slowpoke', 80: 'Slowbro', 81: 'Magnemite', 82: 'Magneton', 83: "Farfetch'd",
    84: 'Doduo', 85: 'Dodrio', 86: 'Seel', 87: 'Dewgong', 88: 'Grimer', 89: 'Muk', 90: 'Shellder',
    91: 'Cloyster', 92: 'Gastly', 93: 'Haunter', 94: 'Gengar', 95: 'Onix', 96: 'Drowzee',
    97: 'Hypno', 98: 'Krabby', 99: 'Kingler', 100: 'Voltorb', 101: 'Electrode', 102: 'Exeggcute',
    103: 'Exeggutor', 104: 'Cubone', 105: 'Marowak', 106: 'Hitmonlee', 107: 'Hitmonchan',
    108: 'Lickitung', 109: 'Koffing', 110: 'Weezing', 111: 'Rhyhorn', 112: 'Rhydon', 113: 'Chansey',
    114: 'Tangela', 115: 'Kangaskhan', 116: 'Horsea', 117: 'Seadra', 118: 'Goldeen', 119: 'Seaking',
    120: 'Staryu', 121: 'Starmie', 122: 'Mr. Mime', 123: 'Scyther', 124: 'Jynx', 125: 'Electabuzz',
    126: 'Magmar', 127: 'Pinsir', 128: 'Tauros', 129: 'Magikarp', 130: 'Gyarados', 131: 'Lapras',
    132: 'Ditto', 133: 'Eevee', 134: 'Vaporeon', 135: 'Jolteon', 136: 'Flareon', 137: 'Porygon',
    138: 'Omanyte', 139: 'Omastar', 140: 'Kabuto', 141: 'Kabutops', 142: 'Aerodactyl', 143: 'Snorlax',
    144: 'Articuno', 145: 'Zapdos', 146: 'Moltres', 147: 'Dratini', 148: 'Dragonair', 149: 'Dragonite',
    150: 'Mewtwo', 151: 'Mew', 152: 'Chikorita', 153: 'Bayleef', 154: 'Meganium', 155: 'Cyndaquil',
    156: 'Quilava', 157: 'Typhlosion', 158: 'Totodile', 159: 'Croconaw', 160: 'Feraligatr',
    161: 'Sentret', 162: 'Furret', 163: 'Hoothoot', 164: 'Noctowl', 165: 'Ledyba', 166: 'Ledian',
    167: 'Spinarak', 168: 'Ariados', 169: 'Crobat', 170: 'Chinchou', 171: 'Lanturn', 172: 'Pichu',
    173: 'Cleffa', 174: 'Igglybuff', 175: 'Togepi', 176: 'Togetic', 177: 'Natu', 178: 'Xatu',
    179: 'Mareep', 180: 'Flaaffy', 181: 'Ampharos', 182: 'Bellossom', 183: 'Marill', 184: 'Azumarill',
    185: 'Sudowoodo', 186: 'Politoed', 187: 'Hoppip', 188: 'Skiploom', 189: 'Jumpluff', 190: 'Aipom',
    191: 'Sunkern', 192: 'Sunflora', 193: 'Yanma', 194: 'Wooper', 195: 'Quagsire', 196: 'Espeon',
    197: 'Umbreon', 198: 'Murkrow', 199: 'Slowking', 200: 'Misdreavus', 201: 'Unown', 202: 'Wobbuffet',
    203: 'Girafarig', 204: 'Pineco', 205: 'Forretress', 206: 'Dunsparce', 207: 'Gligar', 208: 'Steelix',
    209: 'Snubbull', 210: 'Granbull', 211: 'Qwilfish', 212: 'Scizor', 213: 'Shuckle', 214: 'Heracross',
    215: 'Sneasel', 216: 'Teddiursa', 217: 'Ursaring', 218: 'Slugma', 219: 'Magcargo', 220: 'Swinub',
    221: 'Piloswine', 222: 'Corsola', 223: 'Remoraid', 224: 'Octillery', 225: 'Delibird', 226: 'Mantine',
    227: 'Skarmory', 228: 'Houndour', 229: 'Houndoom', 230: 'Kingdra', 231: 'Phanpy', 232: 'Donphan',
    233: 'Porygon2', 234: 'Stantler', 235: 'Smeargle', 236: 'Tyrogue', 237: 'Hitmontop', 238: 'Smoochum',
    239: 'Elekid', 240: 'Magby', 241: 'Miltank', 242: 'Blissey', 243: 'Raikou', 244: 'Entei',
    245: 'Suicune', 246: 'Larvitar', 247: 'Pupitar', 248: 'Tyranitar', 249: 'Lugia', 250: 'Ho-Oh',
    251: 'Celebi', 252: 'Treecko', 253: 'Grovyle', 254: 'Sceptile', 255: 'Torchic', 256: 'Combusken',
    257: 'Blaziken', 258: 'Mudkip', 259: 'Marshtomp', 260: 'Swampert', 261: 'Poochyena',
    262: 'Mightyena', 263: 'Zigzagoon', 264: 'Linoone', 265: 'Wurmple', 266: 'Silcoon', 267: 'Beautifly',
    268: 'Cascoon', 269: 'Dustox', 270: 'Lotad', 271: 'Lombre', 272: 'Ludicolo', 273: 'Seedot',
    274: 'Nuzleaf', 275: 'Shiftry', 276: 'Taillow', 277: 'Swellow', 278: 'Wingull', 279: 'Pelipper',
    280: 'Ralts', 281: 'Kirlia', 282: 'Gardevoir', 283: 'Surskit', 284: 'Masquerain', 285: 'Shroomish',
    286: 'Breloom', 287: 'Slakoth', 288: 'Vigoroth', 289: 'Slaking', 290: 'Nincada', 291: 'Ninjask',
    292: 'Shedinja', 293: 'Whismur', 294: 'Loudred', 295: 'Exploud', 296: 'Makuhita', 297: 'Hariyama',
    298: 'Azurill', 299: 'Nosepass', 300: 'Skitty', 301: 'Delcatty', 302: 'Sableye', 303: 'Mawile',
    304: 'Aron', 305: 'Lairon', 306: 'Aggron', 307: 'Meditite', 308: 'Medicham', 309: 'Electrike',
    310: 'Manectric', 311: 'Plusle', 312: 'Minun', 313: 'Volbeat', 314: 'Illumise', 315: 'Roselia',
    316: 'Gulpin', 317: 'Swalot', 318: 'Carvanha', 319: 'Sharpedo', 320: 'Wailmer', 321: 'Wailord',
    322: 'Numel', 323: 'Camerupt', 324: 'Torkoal', 325: 'Spoink', 326: 'Grumpig', 327: 'Spinda',
    328: 'Trapinch', 329: 'Vibrava', 330: 'Flygon', 331: 'Cacnea', 332: 'Cacturne', 333: 'Swablu',
    334: 'Altaria', 335: 'Zangoose', 336: 'Seviper', 337: 'Lunatone', 338: 'Solrock', 339: 'Barboach',
    340: 'Whiscash', 341: 'Corphish', 342: 'Crawdaunt', 343: 'Baltoy', 344: 'Claydol', 345: 'Lileep',
    346: 'Cradily', 347: 'Anorith', 348: 'Armaldo', 349: 'Feebas', 350: 'Milotic', 351: 'Castform',
    352: 'Kecleon', 353: 'Shuppet', 354: 'Banette', 355: 'Duskull', 356: 'Dusclops', 357: 'Tropius',
    358: 'Chimecho', 359: 'Absol', 360: 'Wynaut', 361: 'Snorunt', 362: 'Glalie', 363: 'Spheal',
    364: 'Sealeo', 365: 'Walrein', 366: 'Clamperl', 367: 'Huntail', 368: 'Gorebyss', 369: 'Relicanth',
    370: 'Luvdisc', 371: 'Bagon', 372: 'Shelgon', 373: 'Salamence', 374: 'Beldum', 375: 'Metang',
    376: 'Metagross', 377: 'Regirock', 378: 'Regice', 379: 'Registeel', 380: 'Latias', 381: 'Latios',
    382: 'Kyogre', 383: 'Groudon', 384: 'Rayquaza', 385: 'Jirachi', 386: 'Deoxys', 387: 'Turtwig',
    388: 'Grotle', 389: 'Torterra', 390: 'Chimchar', 391: 'Monferno', 392: 'Infernape', 393: 'Piplup',
    394: 'Prinplup', 395: 'Empoleon', 396: 'Starly', 397: 'Staravia', 398: 'Staraptor', 399: 'Bidoof',
    400: 'Bibarel', 401: 'Kricketot', 402: 'Kricketune', 403: 'Shinx', 404: 'Luxio', 405: 'Luxray',
    406: 'Budew', 407: 'Roserade', 408: 'Cranidos', 409: 'Rampardos', 410: 'Shieldon', 411: 'Bastiodon',
    412: 'Burmy', 413: 'Wormadam', 414: 'Mothim', 415: 'Combee', 416: 'Vespiquen', 417: 'Pachirisu',
    418: 'Buizel', 419: 'Floatzel', 420: 'Cherubi', 421: 'Cherrim', 422: 'Shellos', 423: 'Gastrodon',
    424: 'Ambipom', 425: 'Drifloon', 426: 'Drifblim', 427: 'Buneary', 428: 'Lopunny', 429: 'Mismagius',
    430: 'Honchkrow', 431: 'Glameow', 432: 'Purugly', 433: 'Chingling', 434: 'Stunky', 435: 'Skuntank',
    436: 'Bronzor', 437: 'Bronzong', 438: 'Bonsly', 439: 'Mime Jr.', 440: 'Happiny', 441: 'Chatot',
    442: 'Spiritomb', 443: 'Gible', 444: 'Gabite', 445: 'Garchomp', 446: 'Munchlax', 447: 'Riolu',
    448: 'Lucario', 449: 'Hippopotas', 450: 'Hippowdon', 451: 'Skorupi', 452: 'Drapion', 453: 'Croagunk',
    454: 'Toxicroak', 455: 'Carnivine', 456: 'Finneon', 457: 'Lumineon', 458: 'Mantyke', 459: 'Snover',
    460: 'Abomasnow', 461: 'Weavile', 462: 'Magnezone', 463: 'Lickilicky', 464: 'Rhyperior',
    465: 'Tangrowth', 466: 'Electivire', 467: 'Magmortar', 468: 'Togekiss', 469: 'Yanmega',
    470: 'Leafeon', 471: 'Glaceon', 472: 'Gliscor', 473: 'Mamoswine', 474: 'Porygon-Z', 475: 'Gallade',
    476: 'Probopass', 477: 'Dusknoir', 478: 'Froslass', 479: 'Rotom', 480: 'Uxie', 481: 'Mesprit',
    482: 'Azelf', 483: 'Dialga', 484: 'Palkia', 485: 'Heatran', 486: 'Regigigas', 487: 'Giratina',
    488: 'Cresselia', 489: 'Phione', 490: 'Manaphy', 491: 'Darkrai', 492: 'Shaymin', 493: 'Arceus',
    494: 'Victini', 495: 'Snivy', 496: 'Servine', 497: 'Serperior', 498: 'Tepig', 499: 'Pignite',
    500: 'Emboar', 501: 'Oshawott', 502: 'Dewott', 503: 'Samurott', 504: 'Patrat', 505: 'Watchog',
    506: 'Lillipup', 507: 'Herdier', 508: 'Stoutland', 509: 'Purrloin', 510: 'Liepard', 511: 'Pansage',
    512: 'Simisage', 513: 'Pansear', 514: 'Simisear', 515: 'Panpour', 516: 'Simipour', 517: 'Munna',
    518: 'Musharna', 519: 'Pidove', 520: 'Tranquill', 521: 'Unfezant', 522: 'Blitzle', 523: 'Zebstrika',
    524: 'Roggenrola', 525: 'Boldore', 526: 'Gigalith', 527: 'Woobat', 528: 'Swoobat', 529: 'Drilbur',
    530: 'Excadrill', 531: 'Audino', 532: 'Timburr', 533: 'Gurdurr', 534: 'Conkeldurr', 535: 'Tympole',
    536: 'Palpitoad', 537: 'Seismitoad', 538: 'Throh', 539: 'Sawk', 540: 'Sewaddle', 541: 'Swadloon',
    542: 'Leavanny', 543: 'Venipede', 544: 'Whirlipede', 545: 'Scolipede', 546: 'Cottonee',
    547: 'Whimsicott', 548: 'Petilil', 549: 'Lilligant', 550: 'Basculin', 551: 'Sandile', 552: 'Krokorok',
    553: 'Krookodile', 554: 'Darumaka', 555: 'Darmanitan', 556: 'Maractus', 557: 'Dwebble', 558: 'Crustle',
    559: 'Scraggy', 560: 'Scrafty', 561: 'Sigilyph', 562: 'Yamask', 563: 'Cofagrigus', 564: 'Tirtouga',
    565: 'Carracosta', 566: 'Archen', 567: 'Archeops', 568: 'Trubbish', 569: 'Garbodor', 570: 'Zorua',
    571: 'Zoroark', 572: 'Minccino', 573: 'Cinccino', 574: 'Gothita', 575: 'Gothorita', 576: 'Gothitelle',
    577: 'Solosis', 578: 'Duosion', 579: 'Reuniclus', 580: 'Ducklett', 581: 'Swanna', 582: 'Vanillite',
    583: 'Vanillish', 584: 'Vanilluxe', 585: 'Deerling', 586: 'Sawsbuck', 587: 'Emolga', 588: 'Karrablast',
    589: 'Escavalier', 590: 'Foongus', 591: 'Amoonguss', 592: 'Frillish', 593: 'Jellicent',
    594: 'Alomomola', 595: 'Joltik', 596: 'Galvantula', 597: 'Ferroseed', 598: 'Ferrothorn',
    599: 'Klink', 600: 'Klang', 601: 'Klinklang', 602: 'Tynamo', 603: 'Eelektrik', 604: 'Eelektross',
    605: 'Elgyem', 606: 'Beheeyem', 607: 'Litwick', 608: 'Lampent', 609: 'Chandelure', 610: 'Axew',
    611: 'Fraxure', 612: 'Haxorus', 613: 'Cubchoo', 614: 'Beartic', 615: 'Cryogonal', 616: 'Shelmet',
    617: 'Accelgor', 618: 'Stunfisk', 619: 'Mienfoo', 620: 'Mienshao', 621: 'Druddigon', 622: 'Golett',
    623: 'Golurk', 624: 'Pawniard', 625: 'Bisharp', 626: 'Bouffalant', 627: 'Rufflet', 628: 'Braviary',
    629: 'Vullaby', 630: 'Mandibuzz', 631: 'Heatmor', 632: 'Durant', 633: 'Deino', 634: 'Zweilous',
    635: 'Hydreigon', 636: 'Larvesta', 637: 'Volcarona', 638: 'Cobalion', 639: 'Terrakion',
    640: 'Virizion', 641: 'Tornadus', 642: 'Thundurus', 643: 'Reshiram', 644: 'Zekrom', 645: 'Landorus',
    646: 'Kyurem', 647: 'Keldeo', 648: 'Meloetta', 649: 'Genesect', 650: 'Chespin', 651: 'Quilladin',
    652: 'Chesnaught', 653: 'Fennekin', 654: 'Braixen', 655: 'Delphox', 656: 'Froakie', 657: 'Frogadier',
    658: 'Greninja', 659: 'Bunnelby', 660: 'Diggersby', 661: 'Fletchling', 662: 'Fletchinder',
    663: 'Talonflame', 664: 'Scatterbug', 665: 'Spewpa', 666: 'Vivillon', 667: 'Litleo', 668: 'Pyroar',
    669: 'Flabébé', 670: 'Floette', 671: 'Florges', 672: 'Skiddo', 673: 'Gogoat', 674: 'Pancham',
    675: 'Pangoro', 676: 'Furfrou', 677: 'Espurr', 678: 'Meowstic', 679: 'Honedge', 680: 'Doublade',
    681: 'Aegislash', 682: 'Spritzee', 683: 'Aromatisse', 684: 'Swirlix', 685: 'Slurpuff', 686: 'Inkay',
    687: 'Malamar', 688: 'Binacle', 689: 'Barbaracle', 690: 'Skrelp', 691: 'Dragalge', 692: 'Clauncher',
    693: 'Clawitzer', 694: 'Helioptile', 695: 'Heliolisk', 696: 'Tyrunt', 697: 'Tyrantrum',
    698: 'Amaura', 699: 'Aurorus', 700: 'Sylveon', 701: 'Hawlucha', 702: 'Dedenne', 703: 'Carbink',
    704: 'Goomy', 705: 'Sliggoo', 706: 'Goodra', 707: 'Klefki', 708: 'Phantump', 709: 'Trevenant',
    710: 'Pumpkaboo', 711: 'Gourgeist', 712: 'Bergmite', 713: 'Avalugg', 714: 'Noibat', 715: 'Noivern',
    716: 'Xerneas', 717: 'Yveltal', 718: 'Zygarde', 719: 'Diancie', 720: 'Hoopa', 721: 'Volcanion',
    722: 'Rowlet', 723: 'Dartrix', 724: 'Decidueye', 725: 'Litten', 726: 'Torracat', 727: 'Incineroar',
    728: 'Popplio', 729: 'Brionne', 730: 'Primarina', 731: 'Pikipek', 732: 'Trumbeak', 733: 'Toucannon',
    734: 'Yungoos', 735: 'Gumshoos', 736: 'Grubbin', 737: 'Charjabug', 738: 'Vikavolt', 739: 'Crabrawler',
    740: 'Crabominable', 741: 'Oricorio', 742: 'Cutiefly', 743: 'Ribombee', 744: 'Rockruff', 745: 'Lycanroc',
    746: 'Wishiwashi', 747: 'Mareanie', 748: 'Toxapex', 749: 'Mudbray', 750: 'Mudsdale', 751: 'Dewpider',
    752: 'Araquanid', 753: 'Fomantis', 754: 'Lurantis', 755: 'Morelull', 756: 'Shiinotic', 757: 'Salandit',
    758: 'Salazzle', 759: 'Stufful', 760: 'Bewear', 761: 'Bounsweet', 762: 'Steenee', 763: 'Tsareena',
    764: 'Comfey', 765: 'Oranguru', 766: 'Passimian', 767: 'Wimpod', 768: 'Golisopod', 769: 'Sandygast',
    770: 'Palossand', 771: 'Pyukumuku', 772: 'Type: Null', 773: 'Silvally', 774: 'Minior', 775: 'Komala',
    776: 'Turtonator', 777: 'Togedemaru', 778: 'Mimikyu', 779: 'Bruxish', 780: 'Drampa', 781: 'Dhelmise',
    782: 'Jangmo-o', 783: 'Hakamo-o', 784: 'Kommo-o', 785: 'Tapu Koko', 786: 'Tapu Lele', 787: 'Tapu Bulu',
    788: 'Tapu Fini', 789: 'Cosmog', 790: 'Cosmoem', 791: 'Solgaleo', 792: 'Lunala', 793: 'Nihilego',
    794: 'Buzzwole', 795: 'Pheromosa', 796: 'Xurkitree', 797: 'Celesteela', 798: 'Kartana', 799: 'Guzzlord',
    800: 'Necrozma', 801: 'Magearna', 802: 'Marshadow', 803: 'Poipole', 804: 'Naganadel', 805: 'Stakataka',
    806: 'Blacephalon', 807: 'Zeraora', 808: 'Meltan', 809: 'Melmetal', 810: 'Grookey', 811: 'Thwackey',
    812: 'Rillaboom', 813: 'Scorbunny', 814: 'Raboot', 815: 'Cinderace', 816: 'Sobble', 817: 'Drizzile',
    818: 'Inteleon', 819: 'Skwovet', 820: 'Greedent', 821: 'Rookidee', 822: 'Corvisquire',
    823: 'Corviknight', 824: 'Blipbug', 825: 'Dottler', 826: 'Orbeetle', 827: 'Nickit', 828: 'Thievul',
    829: 'Gossifleur', 830: 'Eldegoss', 831: 'Wooloo', 832: 'Dubwool', 833: 'Chewtle', 834: 'Drednaw',
    835: 'Yamper', 836: 'Boltund', 837: 'Rolycoly', 838: 'Carkol', 839: 'Coalossal', 840: 'Applin',
    841: 'Flapple', 842: 'Appletun', 843: 'Silicobra', 844: 'Sandaconda', 845: 'Cramorant',
    846: 'Arrokuda', 847: 'Barraskewda', 848: 'Toxel', 849: 'Toxtricity', 850: 'Sizzlipede',
    851: 'Centiskorch', 852: 'Clobbopus', 853: 'Grapploct', 854: 'Sinistea', 855: 'Polteageist',
    856: 'Hatenna', 857: 'Hattrem', 858: 'Hatterene', 859: 'Impidimp', 860: 'Morgrem', 861: 'Grimmsnarl',
    862: 'Obstagoon', 863: 'Perrserker', 864: 'Cursola', 865: "Sirfetch'd", 866: 'Mr. Rime',
    867: 'Runerigus', 868: 'Milcery', 869: 'Alcremie', 870: 'Falinks', 871: 'Pincurchin', 872: 'Snom',
    873: 'Frosmoth', 874: 'Stonjourner', 875: 'Eiscue', 876: 'Indeedee', 877: 'Morpeko', 878: 'Cufant',
    879: 'Copperajah', 880: 'Dracozolt', 881: 'Arctozolt', 882: 'Dracovish', 883: 'Arctovish',
    884: 'Duraludon', 885: 'Dreepy', 886: 'Drakloak', 887: 'Dragapult', 888: 'Zacian', 889: 'Zamazenta',
    890: 'Eternatus', 891: 'Kubfu', 892: 'Urshifu', 893: 'Zarude', 894: 'Regieleki', 895: 'Regidrago',
    896: 'Glastrier', 897: 'Spectrier', 898: 'Calyrex', 899: 'Wyrdeer', 900: 'Kleavor', 901: 'Ursaluna',
    902: 'Basculegion', 903: 'Sneasler', 904: 'Overqwil', 905: 'Enamorus', 906: 'Sprigatito',
    907: 'Floragato', 908: 'Meowscarada', 909: 'Fuecoco', 910: 'Crocalor', 911: 'Skeledirge',
    912: 'Quaxly', 913: 'Quaxwell', 914: 'Quaquaval', 915: 'Lechonk', 916: 'Oinkologne', 917: 'Tarountula',
    918: 'Spidops', 919: 'Nymble', 920: 'Lokix', 921: 'Pawmi', 922: 'Pawmo', 923: 'Pawmot',
    924: 'Tandemaus', 925: 'Maushold', 926: 'Fidough', 927: 'Dachsbun', 928: 'Smoliv', 929: 'Dolliv',
    930: 'Arboliva', 931: 'Squawkabilly', 932: 'Nacli', 933: 'Naclstack', 934: 'Garganacl', 935: 'Charcadet',
    936: 'Armarouge', 937: 'Ceruledge', 938: 'Tadbulb', 939: 'Bellibolt', 940: 'Wattrel',
    941: 'Kilowattrel', 942: 'Maschiff', 943: 'Mabosstiff', 944: 'Shroodle', 945: 'Grafaiai',
    946: 'Bramblin', 947: 'Brambleghast', 948: 'Toedscool', 949: 'Toedscruel', 950: 'Klawf',
    951: 'Capsakid', 952: 'Scovillain', 953: 'Rellor', 954: 'Rabsca', 955: 'Flittle', 956: 'Espathra',
    957: 'Tinkatink', 958: 'Tinkatuff', 959: 'Tinkaton', 960: 'Wiglett', 961: 'Wugtrio', 962: 'Bombirdier',
    963: 'Finizen', 964: 'Palafin', 965: 'Varoom', 966: 'Revavroom', 967: 'Cyclizar', 968: 'Orthworm',
    969: 'Glimmet', 970: 'Glimmora', 971: 'Greavard', 972: 'Houndstone', 973: 'Flamigo', 974: 'Cetoddle',
    975: 'Cetitan', 976: 'Veluza', 977: 'Dondozo', 978: 'Tatsugiri', 979: 'Annihilape', 980: 'Clodsire',
    981: 'Farigiraf', 982: 'Dudunsparce', 983: 'Kingambit', 984: 'Great Tusk', 985: 'Scream Tail',
    986: 'Brute Bonnet', 987: 'Flutter Mane', 988: 'Slither Wing', 989: 'Sandy Shocks', 990: 'Iron Treads',
    991: 'Iron Bundle', 992: 'Iron Hands', 993: 'Iron Jugulis', 994: 'Iron Moth', 995: 'Iron Thorns',
    996: 'Frigibax', 997: 'Arctibax', 998: 'Baxcalibur', 999: 'Gimmighoul', 1000: 'Gholdengo',
    1001: 'Wo-Chien', 1002: 'Chien-Pao', 1003: 'Ting-Lu', 1004: 'Chi-Yu', 1005: 'Roaring Moon',
    1006: 'Iron Valiant', 1007: 'Koraidon', 1008: 'Miraidon', 1009: 'Walking Wake', 1010: 'Iron Leaves',
    1011: 'Dipplin', 1012: 'Poltchageist', 1013: 'Sinistcha', 1014: 'Okidogi',
    1015: 'Munkidori', 1016: 'Fezandipiti', 1017: 'Ogerpon', 1018: 'Archaludon',
    1019: 'Hydrapple', 1020: 'Gouging Fire', 1021: 'Raging Bolt', 1022: 'Iron Boulder',
    1023: 'Iron Crown', 1024: 'Terapagos',
}

# Quest IDs follow the generated catalog order for the Expansion v2.0 build.
MAIN_QUESTS = (
    (0, "To Adventure!", "Embark on your first Adventure"),
    (1, "Gym Badge 1", "Defeat the first gym leader"),
    (2, "Gym Badge 2", "Defeat the second gym leader"),
    (3, "Gym Badge 3", "Defeat the third gym leader"),
    (4, "Gym Badge 4", "Defeat the fourth gym leader"),
    (5, "Gym Badge 5", "Defeat the fifth gym leader"),
    (6, "Gym Badge 6", "Defeat the sixth gym leader"),
    (7, "Gym Badge 7", "Defeat the seventh gym leader"),
    (8, "Gym Badge 8", "Defeat the eighth gym leader"),
    (9, "Elite Master", "Defeat the Elite Four"),
    (10, "Champion", "Defeat the final Champion"),
    (11, "Welcome Home", "Build all of the town areas"),
    (12, "Post Game?", "Meet a mysterious person"),
    (15, "Collector", "Collect data for 15 Pokémon in the Pokédex"),
    (16, "Collector +", "Collect data for 100 Pokémon in the Pokédex"),
    (17, "Collector S", "Collect data for 10 Shiny Pokémon in the Pokédex"),
    (18, "Collector X", "Defeat every Elite Four Trainer with a Legendary Pokémon in your party"),
    (19, "Care Tactics", "Defeat the first four Gym Leaders without your Pokémon ever fainting"),
    (20, "Smart Tactics", "Defeat all eight Gym Leaders without your Pokémon ever fainting"),
    (21, "Mr. Randoman", "Trade a Pokémon with Mr. Randoman"),
    (22, "Shopping Spree", "Spend at least $20,000 during a single visit to a Rest Stop"),
    (23, "Big Saver", "Exit a Rest Stop with at least $50,000"),
    (24, "True Legend", "Catch a Legendary Pokémon"),
    (25, "Shiny a Day", "Catch a Shiny Pokémon"),
    (26, "Hidden Grotto", "Catch a Pokémon from a Hidden Grotto"),
    (27, "Poké Ball, Go!", "Win a Pokémon Catching Contest"),
    (28, "Enticing PokéBLOCK", "Catch a Pokémon at a Honey Tree"),
    (29, "Elo Climb", "Win a battle in the Battle Simulator"),
    (30, "All Skill", "Win every single round in the Game Show"),
    (31, "Fateful Encounter", "Visit the lab to reunite with a friend from the past"),
    (32, "Blasting Off", "Defeat an Evil Team Leader"),
    (33, "Mankey's Paw", "Make a Dark Deal"),
    (34, "Blessing's Favour", "Find some Sacred Ash"),
    (35, "Not Today!", "Use an Escape Rope to avoid a Rival battle"),
    (36, "Double Trouble", "Win a run with the Doubles battle format enabled"),
    (37, "Taste the Rainbow", "Win a run with all nine Generations of Trainers and Rainbow Mode enabled"),
    (38, "Long Haul", "Win a run in Gauntlet Mode"),
    (39, "Battle Gimmick", "Win a run using a Mega Ring, a Z-Power Ring, a Dynamax Band, or a Tera Orb"),
    (40, "Regional Style", "Complete any of the 'Region Style' challenges by enabling a single Generation of trainers with a matching Pokédex"),
    (51, "Type Master", "Complete any of the 'Type Master' challenges by only bringing a single Pokémon Type into battle"),
    (13, "One Last Quest…", 'Complete all other main quests to unlock "The Final Run."'),
    (14, "The Final Run.", "Win a Standard Run with the Pokédex set to National Gen 9 and only Rogue Trainers enabled"),
)

CHALLENGE_QUESTS = (
    (70, "Mega Evolution", "Win a run using a Mega Ring"),
    (71, "Z-Moves", "Win a run using a Z-Power Ring"),
    (72, "Dynamax", "Win a run using a Dynamax Band"),
    (73, "Terastallization", "Win a run using a Tera Orb"),
    (74, "Gimmick Overflow", "Win a run using a Healing Flask, a Mega Ring, a Z-Power Ring, a Dynamax Band, and a Tera Orb"),
    (75, "True Tactics", "Win a run without any Pokémon ever fainting"),
    (76, "Chaos Novice", "Win a run with a Random Starter trade, always doing a Full Party trade with Mr. Randoman whenever possible"),
    (77, "Chaos Master", "Win a run with a Wahey Curse and a Wahey+ Curse"),
    (78, "Roguelocke", "Win a run with a Random Starter trade, an Embargo Curse, a Species Curse, and ten Wild Curses"),
    (79, "Can't Pick!?", "Win a run while entering Trainer battles with only Starter Pokémon in your party"),
    (80, "Diversity", "Win a run while entering Trainer battles with only Pokémon who do not share any types with each other in your party"),
    (81, "Apotheosis", "Win a run while entering Trainer battles with only Legendary Pokémon in your party"),
    (82, "Aesthetics", "Win a run while entering Trainer battles with only Shiny Pokémon in your party"),
    (83, "I am Speed", "Win a run in under 2 hours 30 minutes in-game time"),
    (84, "Cursed Body", "Win a run with a Snowball Curse"),
    (85, "Limited Capture", "Win a run while catching exactly five Pokémon by the end of the run"),
    (86, "BST Crown", "Win a run with a Baby Curse and only using Pokémon with a Base Stat Total of 350 or lower"),
    (87, "Pro-Building", "Win a run with an Auto Move Curse"),
    (88, "Insane Mode", "Win a run with Fresh Start enabled, the Mixed battle format, Random Starter trade, the Embargo, Unaware, and Species Curses, and without ever using Legendary Pokémon"),
    (89, "Iron Mono", "Win a run with five Capacity Curses"),
    (90, "Iron Kaizo", "Win a run with Fresh Start enabled, Random Starter trade, an Embargo Curse, five Capacity Curses, and ninety-nine Discount Curses"),
    (91, "Rocket Triumph", "Defeat the Leader of Team Rocket"),
    (92, "Aqua Triumph", "Defeat the Leader of Team Aqua"),
    (93, "Magma Triumph", "Defeat the Leader of Team Magma"),
    (94, "Galactic Triumph", "Defeat the Leader of Team Galactic"),
    (41, "Kanto Style", "Win a run with the Pokédex set to any Kanto variant with only Kanto Trainers enabled"),
    (42, "Johto Style", "Win a run with the Pokédex set to any Johto variant with only Johto Trainers enabled"),
    (43, "Hoenn Style", "Win a run with the Pokédex set to any Hoenn variant with only Hoenn Trainers enabled"),
    (44, "Sinnoh Style", "Win a run with the Pokédex set to any Sinnoh variant with only Sinnoh Trainers enabled"),
    (45, "Unova Style", "Win a run with the Pokédex set to any Unova variant with only Unova Trainers enabled"),
    (46, "Kalos Style", "Win a run with the Pokédex set to Kalos with only Kalos Trainers enabled"),
    (47, "Alola Style", "Win a run with the Pokédex set to any Alola variant with only Alola Trainers enabled"),
    (48, "Galar Style", "Win a run with the Pokédex set to any Galar variant with only Galar Trainers enabled"),
    (49, "Paldea Style", "Win a run with the Pokédex set to any Paldea variant with only Paldea Trainers enabled"),
    (50, "Orre Style", "Win a run with a Snag Curse, the Doubles battle format, and with Umbreon and Espeon in your party when you enter the Hall of Fame"),
    (52, "Normal Master", "Win a run while entering Trainer battles with only Normal Type Pokémon in your party"),
    (53, "Fighting Master", "Win a run while entering Trainer battles with only Fighting Type Pokémon in your party"),
    (54, "Flying Master", "Win a run while entering Trainer battles with only Flying Type Pokémon in your party"),
    (55, "Poison Master", "Win a run while entering Trainer battles with only Poison Type Pokémon in your party"),
    (56, "Ground Master", "Win a run while entering Trainer battles with only Ground Type Pokémon in your party"),
    (57, "Rock Master", "Win a run while entering Trainer battles with only Rock Type Pokémon in your party"),
    (58, "Bug Master", "Win a run while entering Trainer battles with only Bug Type Pokémon in your party"),
    (59, "Ghost Master", "Win a run while entering Trainer battles with only Ghost Type Pokémon in your party"),
    (60, "Steel Master", "Win a run while entering Trainer battles with only Steel Type Pokémon in your party"),
    (61, "Fire Master", "Win a run while entering Trainer battles with only Fire Type Pokémon in your party"),
    (62, "Water Master", "Win a run while entering Trainer battles with only Water Type Pokémon in your party"),
    (63, "Grass Master", "Win a run while entering Trainer battles with only Grass Type Pokémon in your party"),
    (64, "Electric Master", "Win a run while entering Trainer battles with only Electric Type Pokémon in your party"),
    (65, "Psychic Master", "Win a run while entering Trainer battles with only Psychic Type Pokémon in your party"),
    (66, "Ice Master", "Win a run while entering Trainer battles with only Ice Type Pokémon in your party"),
    (67, "Dragon Master", "Win a run while entering Trainer battles with only Dragon Type Pokémon in your party"),
    (68, "Dark Master", "Win a run while entering Trainer battles with only Dark Type Pokémon in your party"),
    (69, "Fairy Master", "Win a run while entering Trainer battles with only Fairy Type Pokémon in your party"),
)

POKEMON_MASTERIES = (
    (95, "Bulbasaur", "Bulbasaur, Ivysaur, Venusaur"),
    (96, "Charmander", "Charmander, Charmeleon, Charizard"),
    (97, "Squirtle", "Squirtle, Wartortle, Blastoise"),
    (98, "Caterpie", "Caterpie, Metapod, Butterfree"),
    (99, "Weedle", "Weedle, Kakuna, Beedrill"),
    (100, "Pidgey", "Pidgey, Pidgeotto, Pidgeot"),
    (101, "Pichu", "Pichu, Pikachu, Raichu"),
    (102, "Meowth", "Meowth, Persian, Perrserker"),
    (103, "Abra", "Abra, Kadabra, Alakazam"),
    (104, "Machop", "Machop, Machoke, Machamp"),
    (105, "Slowpoke", "Slowpoke, Slowbro, Slowking"),
    (106, "Gastly", "Gastly, Haunter, Gengar"),
    (107, "Onix", "Onix, Steelix"),
    (108, "Krabby", "Krabby, Kingler"),
    (109, "Kangaskhan", "Kangaskhan"),
    (110, "Pinsir", "Pinsir"),
    (111, "Scyther", "Scyther, Scizor, Kleavor"),
    (112, "Magikarp", "Magikarp, Gyarados"),
    (113, "Lapras", "Lapras"),
    (114, "Eevee", "Eevee, Vaporeon, Jolteon, Flareon, Espeon, Umbreon, Leafeon, Glaceon, Sylveon"),
    (115, "Aerodactyl", "Aerodactyl"),
    (116, "Snorlax", "Munchlax, Snorlax"),
    (117, "Mewtwo", "Mewtwo"),
    (118, "Mew", "Mew"),
    (119, "Mareep", "Mareep, Flaaffy, Ampharos"),
    (120, "Heracross", "Heracross"),
    (121, "Houndour", "Houndour, Houndoom"),
    (122, "Larvitar", "Larvitar, Pupitar, Tyranitar"),
    (123, "Treecko", "Treecko, Grovyle, Sceptile"),
    (124, "Torchic", "Torchic, Combusken, Blaziken"),
    (125, "Mudkip", "Mudkip, Marshtomp, Swampert"),
    (126, "Ralts", "Ralts, Kirlia, Gardevoir, Gallade"),
    (127, "Sableye", "Sableye"),
    (128, "Mawile", "Mawile"),
    (129, "Aron", "Aron, Lairon, Aggron"),
    (130, "Meditite", "Meditite, Medicham"),
    (131, "Electrike", "Electrike, Manectric"),
    (132, "Carvanha", "Carvanha, Sharpedo"),
    (133, "Numel", "Numel, Camerupt"),
    (134, "Swablu", "Swablu, Altaria"),
    (135, "Shuppet", "Shuppet, Banette"),
    (136, "Absol", "Absol"),
    (137, "Snorunt", "Snorunt, Glalie, Froslass"),
    (138, "Bagon", "Bagon, Shelgon, Salamence"),
    (139, "Beldum", "Beldum, Metang, Metagross"),
    (140, "Lati", "Latias, Latios"),
    (141, "Latias", "Latias"),
    (142, "Latios", "Latios"),
    (143, "Kyogre", "Kyogre"),
    (144, "Groudon", "Groudon"),
    (145, "Deoxys", "Deoxys"),
    (146, "Buneary", "Buneary, Lopunny"),
    (147, "Gible", "Gible, Gabite, Garchomp"),
    (148, "Riolu", "Riolu, Lucario"),
    (149, "Snover", "Snover, Abomasnow"),
    (150, "Rotom", "Rotom"),
    (151, "Dialga", "Dialga"),
    (152, "Palkia", "Palkia"),
    (153, "Giratina", "Giratina"),
    (154, "Shaymin", "Shaymin"),
    (155, "Arceus", "Arceus"),
    (156, "Audino", "Audino"),
    (157, "Trubbish", "Trubbish, Garbodor"),
    (158, "Genie", "Tornadus, Thundurus, Landorus, Enamorus"),
    (159, "Genesect", "Genesect"),
    (160, "Froakie", "Froakie, Frogadier, Greninja"),
    (161, "Zygarde", "Zygarde"),
    (162, "Diancie", "Diancie"),
    (163, "Hoopa", "Hoopa"),
    (164, "Rowlet", "Rowlet, Dartrix, Decidueye"),
    (165, "Litten", "Litten, Torracat, Incineroar"),
    (166, "Popplio", "Popplio, Brionne, Primarina"),
    (167, "Rockruff", "Rockruff, Lycanroc"),
    (168, "Mimikyu", "Mimikyu"),
    (169, "Silvally", "Type: Null, Silvally"),
    (170, "Jangmo-o", "Jangmo-o, Hakamo-o, Kommo-o"),
    (171, "Tapu", "Tapu Koko, Tapu Lele, Tapu Bulu, Tapu Fini"),
    (172, "Cosmog", "Cosmog, Cosmoem, Solgaleo, Lunala"),
    (173, "Necrozma", "Necrozma"),
    (174, "Magearna", "Magearna"),
    (175, "Marshadow", "Marshadow"),
    (176, "Meltan", "Meltan, Melmetal"),
    (177, "Grookey", "Grookey, Thwackey, Rillaboom"),
    (178, "Scorbunny", "Scorbunny, Raboot, Cinderace"),
    (179, "Sobble", "Sobble, Drizzile, Inteleon"),
    (180, "Rookidee", "Rookidee, Corvisquire, Corviknight"),
    (181, "Blipbug", "Blipbug, Dottler, Orbeetle"),
    (182, "Chewtle", "Chewtle, Drednaw"),
    (183, "Rolycoly", "Rolycoly, Carkol, Coalossal"),
    (184, "Applin", "Applin, Flapple, Appletun, Dipplin, Hydrapple"),
    (185, "Silicobra", "Silicobra, Sandaconda"),
    (186, "Toxel", "Toxel, Toxtricity"),
    (187, "Sizzlipede", "Sizzlipede, Centiskorch"),
    (188, "Hatenna", "Hatenna, Hattrem, Hatterene"),
    (189, "Impidimp", "Impidimp, Morgrem, Grimmsnarl"),
    (190, "Milcery", "Milcery, Alcremie"),
    (191, "Cufant", "Cufant, Copperajah"),
    (192, "Duraludon", "Duraludon, Archaludon"),
    (193, "Zacian", "Zacian"),
    (194, "Zamazenta", "Zamazenta"),
    (195, "Kubfu", "Kubfu, Urshifu"),
    (196, "Ogerpon", "Ogerpon"),
    (197, "Terapagos", "Terapagos"),
)


def read_save_blocks(save_path):
    """Return matching save blocks and storage data from the newest save."""
    saveblock1_by_counter = {}
    saveblock2_by_counter = {}
    storage_by_counter = {}

    with open(save_path, "rb") as f:
        for sector_index in range(NUM_SECTORS):
            raw = f.read(SECTOR_SIZE)
            if len(raw) != SECTOR_SIZE:
                break

            data = raw[:SECTOR_DATA_SIZE]
            sector_id = struct.unpack_from("<H", raw, SECTOR_DATA_SIZE)[0]
            counter = struct.unpack_from("<I", raw, SECTOR_DATA_SIZE + 8)[0]

            if 1 <= sector_id <= 4:
                saveblock1_by_counter.setdefault(counter, {})[sector_id - 1] = data
            elif sector_id == 0:
                saveblock2_by_counter[counter] = data
            elif (
                POKEMON_STORAGE_SECTOR_START
                <= sector_id
                < POKEMON_STORAGE_SECTOR_START + POKEMON_STORAGE_SECTOR_COUNT
            ):
                storage_by_counter.setdefault(counter, {})[
                    sector_id - POKEMON_STORAGE_SECTOR_START
                ] = data

    complete = [
        (
            counter,
            b"".join(sectors[part] for part in range(4)),
            saveblock2_by_counter[counter],
            struct.unpack_from("<I", saveblock2_by_counter[counter], 0x4C)[0],
            b"".join(
                storage_by_counter[counter][part]
                for part in range(POKEMON_STORAGE_SECTOR_COUNT)
            ),
        )
        for counter, sectors in saveblock1_by_counter.items()
        if (
            len(sectors) == 4
            and counter in saveblock2_by_counter
            and counter in storage_by_counter
            and len(storage_by_counter[counter]) == POKEMON_STORAGE_SECTOR_COUNT
        )
    ]

    if not complete:
        raise ValueError(
            "Could not find a complete matching SaveBlock1/SaveBlock2/"
            "Pokémon Storage sector set. Is this an Emerald Rogue v2.0.x save?"
        )

    counter, block, saveblock2, encryption_key, storage = max(
        complete, key=lambda save: save[0]
    )
    return block, counter, encryption_key, storage, saveblock2


def decode_trainer_name(saveblock2):
    """Decode the trainer name from the SaveBlock2 character bytes."""
    name_bytes = saveblock2[
        SAVEBLOCK2_PLAYER_NAME_OFFSET:
        SAVEBLOCK2_PLAYER_NAME_OFFSET + PLAYER_NAME_LENGTH
    ]
    if len(name_bytes) != PLAYER_NAME_LENGTH:
        raise ValueError("SaveBlock2 is too small to read the trainer name.")

    return decode_game_text(name_bytes)


def decode_game_text(name_bytes):
    """Decode Gen 3 character bytes up to the 0xFF terminator."""
    decoded_characters = []
    special_characters = {
        0xAB: "!",
        0xAC: "?",
        0xAD: ".",
        0xAE: "-",
        0xAF: "·",
        0xB0: "...",
        0xB1: "(",
        0xB2: ")",
        0xB3: "“",
        0xB4: "”",
        0xB5: "♂",
        0xB6: "♀",
        0xB7: "$",
        0xB8: ",",
        0xB9: "×",
        0xBA: "/",
    }
    for value in name_bytes:
        if value == 0xFF:
            break
        if value == 0x00:
            decoded_characters.append(" ")
        elif 0xA1 <= value <= 0xAA:
            decoded_characters.append(str(value - 0xA1))
        elif 0xBB <= value <= 0xD4:
            decoded_characters.append(chr(ord("A") + value - 0xBB))
        elif 0xD5 <= value <= 0xEE:
            decoded_characters.append(chr(ord("a") + value - 0xD5))
        elif value in special_characters:
            decoded_characters.append(special_characters[value])
        else:
            decoded_characters.append("?")

    return "".join(decoded_characters).strip() or "Unknown"


def get_hub_name(block, saveblock2):
    """Return the saved hub name if the saved location is a hub map, else None."""
    map_group = struct.unpack_from("<b", block, SAVEBLOCK1_LOCATION_OFFSET)[0]
    if map_group != HUB_MAP_GROUP:
        return None

    name_bytes = saveblock2[
        SAVEBLOCK2_HUB_NAME_OFFSET:SAVEBLOCK2_HUB_NAME_OFFSET + HUB_NAME_LENGTH
    ]
    return decode_game_text(name_bytes)


def read_money(block, encryption_key, storage):
    """Return the hub snapshot money (bank) and live money (wallet)."""
    if len(block) < SAVEBLOCK1_MONEY_OFFSET + 4:
        raise ValueError("SaveBlock1 is too small to read money.")
    if len(storage) < HUB_SNAPSHOT_MONEY_OFFSET + 4:
        raise ValueError("Pokémon Storage data ends before the hub money snapshot.")

    wallet = (
        struct.unpack_from("<I", block, SAVEBLOCK1_MONEY_OFFSET)[0]
        ^ encryption_key
    )
    bank = struct.unpack_from("<I", storage, HUB_SNAPSHOT_MONEY_OFFSET)[0]
    return bank, wallet


def print_save_info(saveblock2, storage):
    """Print save difficulty and play time, returning display and quest details."""
    play_time_end = SAVEBLOCK2_PLAY_TIME_OFFSET + 5
    if len(saveblock2) < play_time_end:
        raise ValueError("SaveBlock2 is too small to read play time.")

    hours, minutes, seconds, vblanks = struct.unpack_from(
        "<HBBB", saveblock2, SAVEBLOCK2_PLAY_TIME_OFFSET
    )
    if hours > 999 or minutes > 59 or seconds > 59 or vblanks > 59:
        raise ValueError(
            "SaveBlock2 contains invalid play-time values "
            f"({hours} hours, {minutes} minutes, {seconds} seconds, "
            f"{vblanks} VBlanks)."
        )

    config_offset = ROGUE_DIFFICULTY_CONFIG_OFFSET
    if len(storage) < config_offset + 2:
        raise ValueError("Pokémon Storage data ends before the difficulty config.")
    toggle_count = struct.unpack_from("<H", storage, config_offset)[0]
    if toggle_count != DIFFICULTY_TOGGLE_BYTE_COUNT:
        raise ValueError(
            "Could not validate the serialized difficulty config "
            f"(found {toggle_count} toggle bytes)."
        )

    range_count_offset = config_offset + 2 + toggle_count
    if len(storage) < range_count_offset + 2:
        raise ValueError("Pokémon Storage data ends before the difficulty ranges.")
    range_count = struct.unpack_from("<H", storage, range_count_offset)[0]
    if range_count not in (7, 9):
        raise ValueError(
            "Could not validate the serialized difficulty config "
            f"(found {range_count} range values)."
        )

    range_values_offset = range_count_offset + 2
    range_values_end = range_values_offset + range_count
    if range_values_end > len(storage):
        raise ValueError("Pokémon Storage data ends before the difficulty config.")

    preset = storage[range_values_offset + DIFFICULTY_RANGE_PRESET_INDEX]
    if preset >= len(DIFFICULTY_PRESETS):
        raise ValueError(f"Save contains an unknown difficulty preset: {preset}.")

    toggle_values = storage[config_offset + 2:range_count_offset]
    range_values = storage[range_values_offset:range_values_end]
    challenge_difficulty = 0
    for difficulty, requirements in enumerate(DIFFICULTY_PRESET_REQUIREMENTS):
        if any(
            bool(toggle_values[toggle_id // 8] & (1 << (toggle_id % 8))) != required
            for toggle_id, required in requirements.items()
        ):
            break
        if any(value < difficulty for value in range_values[:3]):
            break
        challenge_difficulty = difficulty

    print("=" * 35)
    print(" INFO ")
    print("=" * 35)
    print(f"Current Difficulty: {DIFFICULTY_PRESETS[preset]}")
    print(f"Play Time: {hours}:{minutes:02d}:{seconds:02d}")
    return (
        challenge_difficulty,
        DIFFICULTY_PRESETS[preset],
        f"{hours}:{minutes:02d}",
    )


def read_quest_states(storage):
    """Decode v2.0.x EX quest flags by their generated quest IDs."""
    if len(storage) < ROGUE_SAVE_BLOCK_OFFSET + 8:
        raise ValueError("Pokémon Storage data is too small for the Rogue save block.")

    save_version = struct.unpack_from(
        "<H", storage, ROGUE_SAVE_BLOCK_OFFSET
    )[0]
    secret_id = struct.unpack_from(
        "<H", storage, ROGUE_SAVE_BLOCK_OFFSET + 3
    )[0]
    if secret_id != ROGUE_SAVE_SECRET_ID:
        raise ValueError(
            "Could not validate the Rogue save block in Pokémon Storage "
            f"(found secret ID {secret_id})."
        )
    if save_version not in (3, 4):
        raise ValueError(
            "Quest listing supports v2.0.0/v2.0.1 EX save data only "
            f"(found Rogue save version {save_version})."
        )

    quest_count_offset = ROGUE_SAVE_BLOCK_OFFSET + 6
    quest_count = struct.unpack_from("<H", storage, quest_count_offset)[0]
    expected_quest_count = (
        len(MAIN_QUESTS) + len(CHALLENGE_QUESTS) + len(POKEMON_MASTERIES)
    )
    if quest_count != expected_quest_count:
        raise ValueError(
            "Quest catalog does not match this save "
            f"(found {quest_count} quest states; expected {expected_quest_count})."
        )

    states_offset = quest_count_offset + 2
    states_end = states_offset + quest_count * QUEST_STATE_SIZE
    if states_end > len(storage):
        raise ValueError("Pokémon Storage data ends before the quest-state array.")

    return tuple(
        struct.unpack_from(
            "<I", storage, states_offset + quest_id * QUEST_STATE_SIZE
        )[0]
        for quest_id in range(quest_count)
    )


def print_quest_progress(storage):
    """Print main quests, challenges by difficulty, and Pokémon masteries."""
    states = read_quest_states(storage)
    quest_table = max(
        len(title) for _, title, _ in MAIN_QUESTS + CHALLENGE_QUESTS
    ) + 2
    mastery_table = (
        max(
            len(name) + len(" Mastery")
            for _, name, _ in POKEMON_MASTERIES
        )
        + 2
    )
    difficulty_width = max(len(label) for label in QUEST_DIFFICULTIES) + 2
    challenge_table = quest_table + difficulty_width * len(QUEST_DIFFICULTIES)

    print()
    print("=" * challenge_table)
    print(" QUEST COMPLETION ")
    print("=" * challenge_table)
    print("\nMain Quests")
    print(f"{'Quest':<{quest_table}}  Done")
    print(f"{'-' * quest_table}  ----")
    for quest_id, title, _ in MAIN_QUESTS:
        done = "x" if states[quest_id] & QUEST_COMPLETED_MASK else ""
        print(f"{title:<{quest_table}}  {done:>4}")

    print("\nChallenge Quests")
    print(
        f"{'Quest':<{quest_table}}"
        + "".join(f"{label:>{difficulty_width}}" for label in QUEST_DIFFICULTIES)
    )
    print(
        f"{'-' * quest_table}"
        + "".join("-" * difficulty_width for _ in QUEST_DIFFICULTIES)
    )
    for quest_id, title, _ in CHALLENGE_QUESTS:
        state = states[quest_id]
        highest_difficulty = (
            (state >> QUEST_DIFFICULTY_SHIFT) & 0x7
            if state & QUEST_COMPLETED_MASK
            else -1
        )
        marks = "".join(
            f"{'x' if difficulty <= highest_difficulty else '':>{difficulty_width}}"
            for difficulty in range(len(QUEST_DIFFICULTIES))
        )
        print(f"{title:<{quest_table}}{marks}")

    print("\nPokémon Masteries")
    print(f"{'Quest':<{mastery_table}}  Done")
    print(f"{'-' * mastery_table}  ----")
    for quest_id, name, _ in POKEMON_MASTERIES:
        done = "x" if states[quest_id] & QUEST_COMPLETED_MASK else ""
        print(f"{name + ' Mastery':<{mastery_table}}  {done:>4}")


def national_dex_to_species_id(dex_number):
    """Map a National Dex number to this build's internal species ID."""
    if not 1 <= dex_number < POKEMON_GENERATIONS[-1][2]:
        raise ValueError(f"National Dex number is out of range: {dex_number}")
    if dex_number <= 905:
        return dex_number

    for first_dex_number, offset in reversed(GEN9_SPECIES_ID_OFFSETS):
        if dex_number >= first_dex_number:
            return dex_number + offset

    raise ValueError(f"No internal species mapping for National Dex #{dex_number}")


def bit_is_set(bitmask, species_id):
    """Return True if the internal species ID bit is set."""
    byte_index = species_id // 8
    bit_index = species_id % 8
    return bool(bitmask[byte_index] & (1 << bit_index))


def get_pokedex_status(state_bit_0, state_bit_1, species_id):
    """Return the display status encoded by the species' two Pokédex bits."""
    has_state_bit_0 = bit_is_set(state_bit_0, species_id)
    has_state_bit_1 = bit_is_set(state_bit_1, species_id)
    if has_state_bit_0 and has_state_bit_1:
        return "Shiny"
    if has_state_bit_1:
        return "Caught"
    if has_state_bit_0:
        return "Seen"
    return "Undiscovered"


def get_generation_catch_counts(caught):
    """Return caught counts and representative sprites for each generation."""
    return tuple(
        (
            generation[0],
            sum(
                bit_is_set(caught, national_dex_to_species_id(dex_number))
                for dex_number in range(generation[1], generation[2])
            ),
            generation[2] - generation[1],
            generation[4],
        )
        for generation in POKEMON_GENERATIONS
    )


BERRIES_PER_BATCH = 70
BLOCKS_PER_BATCH = 30
HARVEST_PER_PLANT = 9
BERRY_TREE_ARRAY_OFFSET = 0x169C
BERRY_TREE_RECORD_SIZE = 8
BERRY_TREE_DATA_SIZE = 6
BERRY_PLOT_TREE_IDS = (
    (92, 93, 94, 95, 96),
    (77, 78, 79, 80, 81),
    (87, 88, 89, 90, 91),
    (82, 83, 84, 85, 86),
)
BERRY_STAGE_HOURS = {
    1: (16, 17, 18, 19, 20),
    3: (1, 2, 3, 4, 5, 7, 8, 21, 22, 23, 24, 25),
    4: (6,),
    6: (10, 11, 12, 13, 14, 15, 26, 27, 28, 29, 30),
    12: (9,),
    18: tuple(range(31, 54)),
    24: tuple(range(54, 68)),
}
BERRY_STAGE_MINUTES = {
    berry_type: hours * 60
    for hours, berry_types in BERRY_STAGE_HOURS.items()
    for berry_type in berry_types
}
ROOM_GROWTH_MINUTES = 120
BERRY_TREE_STAGES = {
    1: "Planted",
    2: "Sprouted",
    3: "Taller",
    4: "Flowering",
    5: "Berries",
    255: "Sparkling",
}

#	Berry	Tooltip	Pokéblock	Sprite
BERRY_ITEMS = {
    525: ("Cheri", "Cures paralysis.", "Electric", "Cheri"),
    526: ("Chesto", "Cures sleep.", "Psychic", "Chesto"),
    527: ("Pecha", "Cures poison.", "Poison", "Pecha"),
    528: ("Rawst", "Cures a burn.", "Fire", "Rawst"),
    529: ("Aspear", "Cures freezing.", "Ice", "Aspear"),
    530: ("Leppa", "Restores 10 PP to a move when its PP reaches 0.", "Flying", "Leppa"),
    531: ("Oran", "Restores 10 HP when the holder's HP is low.", "HP", "Oran"),
    532: ("Persim", "Cures confusion.", "Normal", "Persim"),
    533: ("Lum", "Cures any major status condition and confusion.", "Normal", "Lum"),
    534: ("Sitrus", "Restores 25% of the holder's max HP when HP is low.", "HP", "Sitrus"),
    535: ("Figy", "Restores 1/3 HP when low.", "Bug", "Figy"),
    536: ("Wiki", "Restores 1/3 HP when low.", "Rock", "Wiki"),
    537: ("Mago", "Restores 1/3 HP when low.", "Ground", "Mago"),
    538: ("Aguav", "Restores 1/3 HP when low.", "Ice", "Aguav"),
    539: ("Iapapa", "Restores 1/3 HP when low.", "Grass", "Iapapa"),
    540: ("Razz", "", "Fire", "Razz"),
    541: ("Bluk", "", "Water", "Razz"),
    542: ("Nanab", "", "Flying", "Mago"),
    543: ("Wepear", "", "Psychic", "Wepear"),
    544: ("Pinap", "", "Electric", "Iapapa"),
    545: ("Pomeg", "Lowers HP EVs by 10.", "HP", "Pomeg"),
    546: ("Kelpsy", "Lowers Attack EVs by 10.", "ATK", "Kelpsy"),
    547: ("Qualot", "Lowers Defense EVs by 10.", "DEF", "Wepear"),
    548: ("Hondew", "Lowers Sp. Atk EVs by 10.", "SP.ATK", "Hondew"),
    549: ("Grepa", "Lowers Sp. Def EVs by 10.", "SP.DEF", "Grepa"),
    550: ("Tamato", "Lowers Speed EVs by 10.", "SPEED", "Tamato"),
    551: ("Cornn", "", "Dark", "Cornn"),
    552: ("Magost", "", "Steel", "Pomeg"),
    553: ("Rabuta", "", "Fighting", "Rabuta"),
    554: ("Nomel", "", "Ghost", "Nomel"),
    555: ("Spelon", "", "Rock", "Spelon"),
    556: ("Pamtree", "", "Dragon", "Pamtre"),
    557: ("Watmel", "", "Bug", "Rabuta"),
    558: ("Durin", "", "Grass", "Durin"),
    559: ("Belue", "", "Water", "Hondew"),
    560: ("Chilan", "Weakens a super-effective Normal-type attack.", "Normal", "Grepa"),
    561: ("Occa", "Weakens a super-effective Fire-type attack.", "Fire", "Occa"),
    562: ("Passho", "Weakens a super-effective Water-type attack.", "Water", "Cornn"),
    563: ("Wacan", "Weakens a super-effective Electric-type attack.", "Electric", "Razz"),
    564: ("Rindo", "Weakens a super-effective Grass-type attack.", "Grass", "Tamato"),
    565: ("Yache", "Weakens a super-effective Ice-type attack.", "Ice", "Yache"),
    566: ("Chople", "Weakens a super-effective Fighting-type attack.", "Fighting", "Chople"),
    567: ("Kebia", "Weakens a super-effective Poison-type attack.", "Poison", "Kebia"),
    568: ("Shuca", "Weakens a super-effective Ground-type attack.", "Ground", "Shuca"),
    569: ("Coba", "Weakens a super-effective Flying-type attack.", "Flying", "Rawst"),
    570: ("Payapa", "Weakens a super-effective Psychic-type attack.", "Psychic", "Payapa"),
    571: ("Tanga", "Weakens a super-effective Bug-type attack.", "Bug", "Tanga"),
    572: ("Charti", "Weakens a super-effective Rock-type attack.", "Rock", "Lansat"),
    573: ("Kasib", "Weakens a super-effective Ghost-type attack.", "Ghost", "Kasib"),
    574: ("Haban", "Weakens a super-effective Dragon-type attack.", "Dragon", "Haban"),
    575: ("Colbur", "Weakens a super-effective Dark-type attack.", "Dark", "Colbur"),
    576: ("Babiri", "Weakens a super-effective Steel-type attack.", "Steel", "Liechi"),
    577: ("Roseli", "Weakens a super-effective Fairy-type attack.", "Fairy", "Roseli"),
    578: ("Liechi", "Raises Attack by one stage when HP is low.", "ATK", "Liechi"),
    579: ("Ganlon", "Raises Defense by one stage when HP is low.", "DEF", "Hondew"),
    580: ("Salac", "Raises Speed by one stage when HP is low.", "SPEED", "Aguav"),
    581: ("Petaya", "Raises Sp. Atk by one stage when HP is low.", "SP.ATK", "Pomeg"),
    582: ("Apicot", "Raises Sp. Def by one stage when HP is low.", "SP.DEF", "Grepa"),
    583: ("Lansat", "Raises critical-hit ratio when HP is low.", "Ground", "Lansat"),
    584: ("Starf", "Sharply raises one random stat when HP is low.", "SHINY", "Cornn"),
    585: ("Enigma", "Restores HP when the holder is hit by a super-effective attack.", "—", "Durin"),
    586: ("Micle", "Raises accuracy of the holder's next move when HP is low.", "HP", "Micle"),
    587: ("Custap", "Allows the holder to move first when HP is low.", "SPEED", "Custap"),
    588: ("Jaboca", "Damages an attacker that hits the holder with a physical move.", "ATK", "Jaboca"),
    589: ("Rowap", "Damages an attacker that hits the holder with a special move.", "SP.ATK", "Rowap"),
    590: ("Kee", "Raises Defense when the holder is hit by a physical attack.", "Fairy", "Pecha"),
    591: ("Maranga", "Raises Sp. Def when the holder is hit by a special attack.", "SP.DEF", "Occa"),
    599: ("Enigma", "", "—", ""),
}

BERRY_TYPE_NAMES = {
    item_id - 524: berry_data[0]
    for item_id, berry_data in BERRY_ITEMS.items()
}

POKEBLOCK_ITEMS = {
    865: "SHINY", 866: "HP", 867: "ATK", 868: "DEF",
    870: "SP.ATK", 871: "SP.DEF", 869: "SPEED",
    847: "Normal", 856: "Fire", 857: "Water", 859: "Electric",
    858: "Grass", 861: "Ice", 848: "Fighting", 850: "Poison",
    851: "Ground", 849: "Flying", 860: "Psychic", 853: "Bug",
    852: "Rock", 854: "Ghost", 862: "Dragon", 863: "Dark",
    855: "Steel", 864: "Fairy",
}


def decode_bag(block, encryption_key):
    """Decode the actual bag from SaveBlock1."""
    decoded = {}

    for i in range(BAG_ITEM_SLOT_COUNT):
        item_id, encrypted_quantity = struct.unpack_from(
            "<HH", block, BAG_ITEMS_OFFSET + i * 4
        )
        if item_id == 0:
            continue

        quantity = encrypted_quantity ^ (encryption_key & 0xFFFF)
        decoded[item_id] = decoded.get(item_id, 0) + quantity

    return decoded


def read_berry_plots(block):
    """Decode saved hub berry-tree records using the documented field layout."""
    plots = []

    for tree_ids in BERRY_PLOT_TREE_IDS:
        plot = []
        for tree_id in tree_ids:
            offset = BERRY_TREE_ARRAY_OFFSET + tree_id * BERRY_TREE_RECORD_SIZE
            if offset + BERRY_TREE_DATA_SIZE > len(block):
                raise ValueError(
                    f"SaveBlock1 is too small for berry tree {tree_id}."
                )

            berry_type, status, minutes, berry_yield, flags = (
                struct.unpack_from("<BBHBB", block, offset)
            )
            stage = 255 if status == 0xFF else status & 0x7F
            stop_growth = bool(status & 0x80)
            regrowth_count = flags & 0x0F
            watered_stages = tuple(
                bool(flags & (1 << bit)) for bit in range(4, 8)
            )

            if (
                berry_type == 0
                and stage == 0
                and minutes == 0
                and berry_yield == 0
                and flags == 0
            ):
                plot.append({
                    "tree_id": tree_id,
                    "berry": None,
                    "berry_type": berry_type,
                    "stage": 0,
                    "yield": 0,
                    "stop_growth": stop_growth,
                    "minutes_until_next_stage": minutes,
                    "regrowth_count": regrowth_count,
                    "watered_stages": watered_stages,
                    "valid": True,
                })
                continue

            valid = (
                berry_type in BERRY_TYPE_NAMES
                and stage in BERRY_TREE_STAGES
                and berry_type != 0
                and stage != 0
            )
            plot.append({
                "tree_id": tree_id,
                "berry": BERRY_TYPE_NAMES.get(
                    berry_type, f"Unknown berry type {berry_type}"
                ),
                "berry_type": berry_type,
                "stage": stage,
                "yield": berry_yield,
                "stop_growth": stop_growth,
                "minutes_until_next_stage": minutes,
                "regrowth_count": regrowth_count,
                "watered_stages": watered_stages,
                "valid": valid,
            })

        plots.append(plot)

    return plots


def get_rooms_until_harvest(plots):
    """Return rooms to enter until every growing tree bears berries, or None."""
    rooms_needed = 0
    found_growing = False

    for plot in plots:
        for tree in plot:
            stage = tree["stage"]
            if not tree["valid"] or stage == 0 or stage >= 5:
                continue
            stage_minutes = BERRY_STAGE_MINUTES.get(tree["berry_type"])
            if stage_minutes is None or tree["stop_growth"]:
                continue

            remaining = (
                tree["minutes_until_next_stage"]
                + (4 - stage) * stage_minutes
            )
            found_growing = True
            rooms_needed = max(
                rooms_needed, -(-remaining // ROOM_GROWTH_MINUTES)
            )

    return rooms_needed if found_growing else None


def get_berry_harvest(plots):
    """Return projected berry harvest totals from valid planted trees."""
    harvest = {}
    for plot in plots:
        for tree in plot:
            if tree["valid"] and tree["stage"] > 0:
                berry = tree["berry"]
                harvest[berry] = harvest.get(berry, 0) + HARVEST_PER_PLANT
    return harvest


def get_pokeblock_gains(bag):
    """Return Pokéblock quantities available from the berries currently held."""
    gains = {}
    for item_id, berry_data in BERRY_ITEMS.items():
        current = bag.get(item_id, 0)
        if current == 0:
            continue
        block_type = berry_data[2].replace(".", "")
        if block_type == "—":
            continue
        available_blocks = (
            current // BERRIES_PER_BATCH
        ) * BLOCKS_PER_BATCH
        gains[block_type] = gains.get(block_type, 0) + available_blocks
    return gains


def print_berry_and_pokeblock_info(bag, plots, harvest):
    """Print dynamic bag contents and projected berry/pokéblock totals."""
    invalid_tree_count = 0

    print()
    print("=" * 60)
    print(" BERRY PLOTS AND HARVEST ")
    print("=" * 60)

    for i, plot in enumerate(plots, 1):
        print(f"\nPlot {i}")
        print(f"{'Tree':>6}  {'Berry':<20}  Stage")
        print(f"{'-' * 6}  {'-' * 20}  {'-' * 10}")
        for tree in plot:
            if tree["berry"] is None:
                print(f"{tree['tree_id']:>6}  {'(empty)':<20}  -")
            elif not tree["valid"]:
                invalid_tree_count += 1
                print(f"{tree['tree_id']:>6}  {tree['berry']:<20}  Invalid record")
            else:
                stage_name = BERRY_TREE_STAGES[tree["stage"]]
                print(
                    f"{tree['tree_id']:>6}  "
                    f"{(tree['berry'] + ' Berry'):<20}  {stage_name}"
                )
    print("\nFuture harvest estimate")
    print("-" * 60)
    if harvest:
        for berry, qty in sorted(harvest.items()):
            print(f"  {berry + ' Berry':<24} {qty:>4}")
    else:
        print("  No planted berry trees.")

    if invalid_tree_count:
        print(
            f"\nWarning: {invalid_tree_count} tree record(s) were unrecognized "
            "and excluded from the harvest estimate."
        )

    current_blocks = {
        name: bag.get(item_id, 0)
        for item_id, name in POKEBLOCK_ITEMS.items()
    }

    gains = get_pokeblock_gains(bag)

    print("\nPokéblocks")
    print("-" * 60)
    print(f"{'Type':<12} {'In bag':>10} {'From bag berries':>20}")
    print(f"{'-' * 12} {'-' * 10} {'-' * 20}")
    for block_type in POKEBLOCK_ITEMS.values():
        qty = current_blocks.get(block_type, 0)
        gain = gains.get(block_type, 0)
        print(f"{block_type:<12} {qty:>10} {gain:>20}")

    print("\nBerries")
    print("-" * 60)
    print(f"{'#':>3}  {'Berry':<24} {'In bag':>10} {'Harvest':>10}")
    print(f"{'-' * 3}  {'-' * 24} {'-' * 10} {'-' * 10}")
    for item_id in sorted(BERRY_ITEMS):
        berry = BERRY_ITEMS[item_id][0]
        qty = bag.get(item_id, 0)
        harvest_qty = harvest.get(berry, 0)
        if qty == 0 and harvest_qty == 0:
            continue
        berry_number = item_id - 524
        print(
            f"{berry_number:>3}  {(berry + ' Berry'):<24} "
            f"{qty:>10} {harvest_qty:>10}"
        )


def crop_tree_sprite(image, frame_index):
    """Return a 16-by-32 crop from a horizontal tree-sprite strip."""
    frame = tk.PhotoImage(width=16, height=32)
    left = frame_index * 16
    frame.tk.call(
        str(frame),
        "copy",
        str(image),
        "-from",
        left,
        0,
        left + 16,
        32,
    )
    return frame


def crop_sprite_sheet(image, sprite_index, sprite_width, sprite_height, columns):
    """Return one indexed sprite from a row-major sprite sheet."""
    if sprite_index < 0 or columns < 1:
        raise ValueError("Sprite index must be non-negative and columns positive.")

    column = sprite_index % columns
    row = sprite_index // columns
    left = column * sprite_width
    top = row * sprite_height
    if left + sprite_width > image.width() or top + sprite_height > image.height():
        raise ValueError(
            f"Sprite index {sprite_index} is outside the "
            f"{image.width()}x{image.height()} sprite sheet."
        )

    sprite = tk.PhotoImage(width=sprite_width, height=sprite_height)
    sprite.tk.call(
        str(sprite),
        "copy",
        str(image),
        "-from",
        left,
        top,
        left + sprite_width,
        top + sprite_height,
    )
    return sprite


def bind_tree_tooltip(widget, text):
    """Show the supplied text in a small tooltip while the widget is hovered."""
    if text is None:
        return

    tooltip_state = {"window": None}

    def show_tooltip(event):
        """Create the hover tooltip beside the pointer."""
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{event.x_root + 12}+{event.y_root + 12}")
        tk.Label(
            tooltip,
            text=text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padx=4,
            pady=2,
        ).pack()
        tooltip_state["window"] = tooltip

    def hide_tooltip(_event):
        """Close the hover tooltip when the pointer leaves the tree."""
        if _event.widget is not widget:
            return
        tooltip = tooltip_state["window"]
        if tooltip is not None:
            tooltip.destroy()
            tooltip_state["window"] = None

    widget.bind("<Enter>", show_tooltip)
    widget.bind("<Leave>", hide_tooltip)


def bind_canvas_tooltip(canvas, item_id, text):
    """Show the supplied text in a canvas tooltip while the item is hovered."""
    if text is None:
        return

    tooltip_state = {"window": None}

    def show_tooltip(event):
        """Create the hover tooltip beside the pointer."""
        tooltip = tk.Toplevel(canvas)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{event.x_root + 12}+{event.y_root + 12}")
        tk.Label(
            tooltip,
            text=text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padx=4,
            pady=2,
        ).pack()
        tooltip_state["window"] = tooltip

    def hide_tooltip(_event):
        """Close the hover tooltip when the pointer leaves the canvas item."""
        tooltip = tooltip_state["window"]
        if tooltip is not None:
            tooltip.destroy()
            tooltip_state["window"] = None

    canvas.tag_bind(item_id, "<Enter>", show_tooltip)
    canvas.tag_bind(item_id, "<Leave>", hide_tooltip)


def show_berry_plots(
    plots,
    bag,
    harvest,
    seen,
    caught,
    quest_states,
    challenge_difficulty,
    trainer_name,
    difficulty_name,
    play_time,
    bank_money,
    wallet_money,
    hub_name,
):
    """Show the save dashboard with plots, stats, quests, bag, and Pokédex."""
    root = tk.Tk()
    root.title("Emerald Rogue Companion")
    root.configure(background="#73C5A4")
    root.resizable(True, True)
    root.minsize(760, 600)

    scrollbar_style = ttk.Style(root)
    scrollbar_style.theme_use("clam")
    scrollbar_style.layout(
        "Slim.Vertical.TScrollbar",
        [
            (
                "Vertical.Scrollbar.trough",
                {
                    "sticky": "ns",
                    "children": [
                        (
                            "Vertical.Scrollbar.thumb",
                            {"expand": "1", "sticky": "nswe"},
                        )
                    ],
                },
            )
        ],
    )
    scrollbar_style.configure(
        "Slim.Vertical.TScrollbar",
        arrowsize=SCROLLBAR_WIDTH,
        background="#36745D",
        troughcolor="#73C5A4",
        bordercolor="#73C5A4",
        lightcolor="#36745D",
        darkcolor="#36745D",
        relief="flat",
    )
    root.grid_columnconfigure(0, weight=1, minsize=230)
    root.grid_columnconfigure(1, weight=0, minsize=150)
    root.grid_columnconfigure(2, weight=0, minsize=150)
    root.grid_columnconfigure(3, weight=0, minsize=DEX_TABLE_WIDTH + 20)
    root.grid_rowconfigure(1, weight=1)

    berry_sprite_directory = Path(__file__).resolve().parent / "Berry Trees"
    source_images = {}
    frame_cache = {}
    animation_items = []
    empty_image = tk.PhotoImage(width=16, height=32)
    dirt_image = tk.PhotoImage(
        file=str(berry_sprite_directory / "BerryTreeDirtPile.png")
    )
    if dirt_image.width() != 16 or dirt_image.height() != 32:
        raise ValueError("BerryTreeDirtPile.png must be 16x32 pixels.")

    def get_frames(filename, frame_indices):
        """Load and cache the requested 16-by-32 frames from a sprite sheet."""
        cache_key = (filename, tuple(frame_indices))
        if cache_key not in frame_cache:
            if filename not in source_images:
                source_images[filename] = tk.PhotoImage(
                    file=str(berry_sprite_directory / filename)
                )
            source = source_images[filename]
            required_width = (max(frame_indices) + 1) * 16
            if source.width() < required_width or source.height() < 32:
                raise ValueError(
                    f"{filename} is too small for the requested 16x32 frames."
                )
            frame_cache[cache_key] = tuple(
                crop_tree_sprite(source, frame_index)
                for frame_index in frame_indices
            )
        return frame_cache[cache_key]

    dex_frame = tk.LabelFrame(
        root,
        text="Pokédex",
        background="#73C5A4",
        padx=6,
        pady=4,
    )
    dex_frame.grid(
        row=0,
        column=3,
        rowspan=2,
        padx=(0, 8),
        pady=3,
        sticky="nsew",
    )

    dex_filters = tk.Frame(dex_frame, background="#73C5A4")
    dex_filters.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
    show_caught = tk.BooleanVar(root, value=False)
    show_seen = tk.BooleanVar(root, value=True)
    show_undiscovered = tk.BooleanVar(root, value=True)
    show_shiny = tk.BooleanVar(root, value=False)
    dex_row_height = 26
    dex_table_width = DEX_TABLE_WIDTH
    dex_status_x = dex_table_width - 10
    dex_icon_x = 50
    dex_name_x = 68
    dex_name_width = dex_status_x - 8 - 6 - dex_name_x
    dex_name_font = tkfont.nametofont("TkDefaultFont")

    dex_entries = []
    sprite_directory = Path(__file__).resolve().parent / "Sprites"
    pokemon_sheets = {}
    pokemon_icons = {}

    def get_pokemon_icon(dex_number):
        """Load and cache a 32-by-32 sprite for the supplied Dex number."""
        if dex_number not in pokemon_icons:
            generation = next(
                (
                    (first_dex, filename)
                    for first_dex, last_dex, filename
                    in POKEMON_GENERATION_SHEETS
                    if first_dex <= dex_number < last_dex
                ),
                None,
            )
            if generation is None:
                raise ValueError(
                    f"No generation sprite sheet for Dex #{dex_number}."
                )

            first_dex, filename = generation
            if filename not in pokemon_sheets:
                sheet = tk.PhotoImage(file=str(sprite_directory / filename))
                if (
                    sheet.width() != POKEMON_SPRITE_SIZE * POKEMON_SPRITES_PER_ROW
                    or sheet.height() % POKEMON_SPRITE_SIZE != 0
                ):
                    raise ValueError(
                        f"{filename} must be a 12-column sheet of "
                        "32x32 Pokémon sprites."
                    )
                pokemon_sheets[filename] = sheet

            pokemon_icons[dex_number] = crop_sprite_sheet(
                pokemon_sheets[filename],
                dex_number - first_dex,
                POKEMON_SPRITE_SIZE,
                POKEMON_SPRITE_SIZE,
                POKEMON_SPRITES_PER_ROW,
            )
        return pokemon_icons[dex_number]

    def update_dex_filter():
        """Show only Pokédex rows selected by the status filter checkboxes."""
        visible_statuses = set()
        if show_caught.get():
            visible_statuses.add("Caught")
        if show_seen.get():
            visible_statuses.add("Seen")
        if show_undiscovered.get():
            visible_statuses.add("Undiscovered")
        if show_shiny.get():
            visible_statuses.add("Shiny")

        dex_canvas.delete("dex_row")
        visible_row = 0
        for dex_number, name, status in dex_entries:
            if status in visible_statuses:
                y = visible_row * dex_row_height + dex_row_height // 2
                display_name = name
                if dex_name_font.measure(display_name) > dex_name_width:
                    while (
                        display_name
                        and dex_name_font.measure(display_name + "...") > dex_name_width
                    ):
                        display_name = display_name[:-1]
                    display_name = display_name.rstrip() + "..."
                dex_canvas.create_text(
                    4,
                    y,
                    text=f"#{dex_number:03}",
                    anchor="w",
                    tags=("dex_row",),
                )
                dex_canvas.create_image(
                    dex_icon_x,
                    y,
                    image=get_pokemon_icon(dex_number),
                    anchor="center",
                    tags=("dex_row",),
                )
                dex_canvas.create_text(
                    dex_name_x,
                    y,
                    text=display_name,
                    anchor="w",
                    tags=("dex_row",),
                )
                dex_canvas.create_image(
                    dex_status_x,
                    y,
                    image=status_icons[status],
                    tags=("dex_row",),
                )
                visible_row += 1
        dex_canvas.configure(
            scrollregion=(0, 0, dex_table_width, visible_row * dex_row_height)
        )
        dex_canvas.yview_moveto(0)

    def toggle_caught_filter():
        """Mirror the Caught checkbox state to Shiny and refresh the list."""
        show_shiny.set(show_caught.get())
        update_dex_filter()

    for label, variable, row, column in (
        ("Shiny", show_shiny, 0, 0),
        ("Caught", show_caught, 0, 1),
        ("Seen", show_seen, 1, 0),
        ("Undiscovered", show_undiscovered, 1, 1),
    ):
        tk.Checkbutton(
            dex_filters,
            text=label,
            variable=variable,
            command=(
                toggle_caught_filter
                if variable is show_caught
                else update_dex_filter
            ),
            background="#73C5A4",
            activebackground="#73C5A4",
        ).grid(row=row, column=column, padx=(0, 2), sticky="w")

    status_sheet = tk.PhotoImage(file=str(sprite_directory / "Status.png"))
    if (
        status_sheet.width() != len(STATUS_SPRITE_NAMES) * STATUS_SPRITE_SIZE
        or status_sheet.height() != STATUS_SPRITE_SIZE
    ):
        raise ValueError("Status.png must contain four horizontal 12x12 sprites.")
    status_icons = {
        status: crop_sprite_sheet(
            status_sheet,
            index,
            STATUS_SPRITE_SIZE,
            STATUS_SPRITE_SIZE,
            len(STATUS_SPRITE_NAMES),
        )
        for index, status in enumerate(STATUS_SPRITE_NAMES)
    }
    dex_header = tk.Frame(dex_frame, background="#73C5A4")
    dex_header.grid(row=1, column=0, sticky="ew")
    dex_header.configure(width=dex_table_width)
    dex_header.grid_propagate(False)
    dex_header.grid_columnconfigure(2, weight=1)
    dex_header.grid_columnconfigure(1, minsize=30)
    dex_header.grid_columnconfigure(3, minsize=16)
    tk.Label(
        dex_header,
        text="#",
        width=4,
        anchor="w",
        font=("TkDefaultFont", 9, "bold"),
        background="#73C5A4",
    ).grid(row=0, column=0, sticky="w")
    tk.Label(
        dex_header,
        text="",
        width=0,
        anchor="center",
        font=("TkDefaultFont", 9, "bold"),
        background="#73C5A4",
    ).grid(row=0, column=1, sticky="ew", padx=0)
    tk.Label(
        dex_header,
        text="Name",
        width=5,
        anchor="w",
        font=("TkDefaultFont", 9, "bold"),
        background="#73C5A4",
    ).grid(row=0, column=2, sticky="w")
    tk.Label(
        dex_header,
        image=status_icons["Caught"],
        background="#73C5A4",
    ).grid(row=0, column=3, sticky="e")
    dex_canvas = tk.Canvas(
        dex_frame,
        width=dex_table_width,
        height=400,
        background="#73C5A4",
        highlightthickness=0,
        borderwidth=0,
    )
    dex_scrollbar = ttk.Scrollbar(
        dex_frame,
        orient="vertical",
        style="Slim.Vertical.TScrollbar",
        command=dex_canvas.yview,
    )
    dex_canvas.configure(yscrollcommand=dex_scrollbar.set)
    dex_canvas.grid(row=2, column=0, sticky="nsew")
    dex_scrollbar.grid(row=2, column=1, sticky="ns")
    dex_frame.grid_rowconfigure(2, weight=1)
    dex_frame.grid_columnconfigure(0, weight=1)

    for dex_number in range(1, NUM_POKEMON + 1):
        species_id = national_dex_to_species_id(dex_number)
        status = get_pokedex_status(seen, caught, species_id)
        dex_entries.append(
            (
                dex_number,
                POKEMON_NAMES.get(dex_number, f"Pokémon #{dex_number}"),
                status,
            )
        )

    update_dex_filter()
    plots_frame = tk.LabelFrame(
        root,
        text="Berry Plots",
        background="#73C5A4",
        padx=4,
        pady=2,
    )
    plots_frame.grid(
        row=0,
        column=0,
        columnspan=3,
        padx=8,
        pady=3,
        sticky="nsew",
    )
    for column in range(4):
        plots_frame.grid_columnconfigure(column, weight=1)
    plot_gap = 28
    for plot_index, plot in enumerate(plots, 1):
        plot_frame = tk.Frame(plots_frame, background="#73C5A4")
        plot_frame.grid(
            row=1 if plot_index <= 2 else 0,
            column=plot_index - 1,
            padx=(0 if plot_index == 1 else plot_gap, 0),
            sticky="nw",
        )

        for tree_index, tree in enumerate(plot):
            canvas = tk.Canvas(
                plot_frame,
                width=16,
                height=32,
                background="#73C5A4",
                highlightthickness=0,
                borderwidth=0,
            )
            canvas.grid(row=0, column=tree_index, padx=3, pady=3)

            berry = tree["berry"]
            stage = tree["stage"]
            frames = ()
            if berry is None or stage == 0:
                frames = (empty_image,)
                tooltip_text = "Empty tree"
            else:
                tooltip_text = f"{berry} Berry"
                if stage == 1:
                    frames = (dirt_image,)
                elif stage == 2:
                    frames = get_frames("SproutTree.png", (0, 1))
                elif stage in (3, 4, 5, 255):
                    berry_data = BERRY_ITEMS.get(
                        tree["berry_type"] + 524
                    )
                    if berry_data and berry_data[3]:
                        first_frame = {3: 0, 4: 2, 5: 4, 255: 4}[stage]
                        frames = get_frames(
                            f"{berry_data[3]}Tree.png",
                            (first_frame, first_frame + 1),
                        )

            if frames:
                image_id = canvas.create_image(
                    0, 0, anchor="nw", image=frames[0]
                )
                animation_items.append((canvas, image_id, frames))
            else:
                canvas.create_text(8, 16, text="?", fill="white")
            bind_tree_tooltip(canvas, tooltip_text)

    berry_suffix = " Berry" if len(harvest) <= 3 else ""
    harvest_text = " - ".join(
        f"{berry}{berry_suffix} x{quantity}"
        for berry, quantity in sorted(harvest.items())
    )
    if not harvest_text:
        harvest_text = "None"
    tk.Label(
        plots_frame,
        text=harvest_text,
        background="#73C5A4",
        anchor="w",
        justify="left",
        wraplength=500,
    ).grid(
        padx=4,
        pady=(4, 6),
        sticky="ew",
        row=0,
        column=0,
        columnspan=2,
    )

    rooms_left = get_rooms_until_harvest(plots)
    if rooms_left is None:
        ready_text = ""
    elif rooms_left == 0:
        ready_text = "All berries ready to harvest"
    else:
        ready_text = (
            f"All berries ready to harvest in {rooms_left} "
            f"{'stage' if rooms_left == 1 else 'stages'}"
        )
    if ready_text:
        tk.Label(
            plots_frame,
            text=ready_text,
            background="#73C5A4",
            anchor="w",
            justify="left",
            wraplength=250,
        ).grid(
            padx=(28, 4),
            pady=(4, 6),
            sticky="nw",
            row=1,
            column=2,
            columnspan=2,
        )

    stats_frame = tk.LabelFrame(
        root,
        text="Stats",
        background="#73C5A4",
        padx=6,
        pady=4,
    )
    stats_frame.grid(
        row=1,
        column=0,
        padx=(8, 3),
        pady=(0, 8),
        sticky="nsew",
    )
    if hub_name is None:
        trainer_line = f"Trainer {trainer_name} is on an adventure!"
        play_time_label = "Adventuretime"
    else:
        trainer_line = f"Trainer {trainer_name} is resting in {hub_name}."
        play_time_label = "Playtime"
    stat_lines = [
        trainer_line,
        f"Difficulty: {difficulty_name}",
        f"{play_time_label}: {play_time}",
    ]
    if hub_name is None:
        stat_lines.append(f"Wallet: {wallet_money:,}₽")
        stat_lines.append(f"Bank: {bank_money:,}₽")
    else:
        stat_lines.append(f"Bank: {wallet_money:,}₽")
    for row, text in enumerate(stat_lines):
        tk.Label(
            stats_frame,
            text=text,
            background="#73C5A4",
            anchor="w",
        ).grid(row=row, column=0, columnspan=2, sticky="w")
    stats_frame.grid_columnconfigure(0, weight=0, minsize=36)
    stats_frame.grid_columnconfigure(1, weight=1)
    for row, (generation, caught_count, total_count, representative_dex) in enumerate(
        get_generation_catch_counts(caught),
        start=len(stat_lines),
    ):
        icon = (
            status_icons["Shiny"]
            if caught_count == total_count
            else get_pokemon_icon(representative_dex)
        )
        icon_cell = tk.Frame(
            stats_frame, width=36, height=28, background="#73C5A4"
        )
        icon_cell.grid(row=row, column=0, sticky="w", padx=(0, 4))
        icon_cell.grid_propagate(False)
        icon_cell.pack_propagate(False)
        tk.Label(
            icon_cell,
            image=icon,
            background="#73C5A4",
        ).pack(expand=True)
        text_cell = tk.Frame(stats_frame, height=28, background="#73C5A4")
        text_cell.grid(row=row, column=1, sticky="ew")
        text_cell.pack_propagate(False)
        tk.Label(
            text_cell,
            text=f"{generation} Dex:",
            background="#73C5A4",
            anchor="w",
        ).pack(side="left", fill="y")
        tk.Label(
            text_cell,
            text=f"{caught_count}/{total_count}",
            background="#73C5A4",
            anchor="e",
        ).pack(side="right", fill="y")

    bag_frame = tk.LabelFrame(
        root,
        text="Bag",
        background="#73C5A4",
        padx=6,
        pady=4,
    )
    bag_frame.grid(
        row=1,
        column=1,
        padx=3,
        pady=(0, 8),
        sticky="nsew",
    )
    bag_frame.grid_columnconfigure(0, weight=1)
    bag_frame.grid_rowconfigure(0, weight=1)
    bag_canvas = tk.Canvas(
        bag_frame,
        width=200,
        height=400,
        background="#73C5A4",
        highlightthickness=0,
        borderwidth=0,
    )
    bag_scrollbar = ttk.Scrollbar(
        bag_frame,
        orient="vertical",
        style="Slim.Vertical.TScrollbar",
        command=bag_canvas.yview,
    )
    bag_canvas.configure(yscrollcommand=bag_scrollbar.set)
    bag_canvas.grid(row=0, column=0, sticky="nsew")
    bag_scrollbar.grid(row=0, column=1, sticky="ns")
    bag_contents = tk.Frame(bag_canvas, background="#73C5A4")
    bag_contents_window = bag_canvas.create_window(
        (0, 0),
        window=bag_contents,
        anchor="nw",
    )
    bag_row_labels = []

    def update_bag_scroll_region(event):
        if event.widget is bag_contents:
            bag_canvas.configure(scrollregion=bag_canvas.bbox("all"))

    def resize_bag_contents(event):
        bag_canvas.itemconfigure(bag_contents_window, width=event.width)
        for row_label in bag_row_labels:
            row_label.configure(wraplength=max(100, event.width - 8))

    def scroll_bag(event):
        bag_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    bag_contents.bind("<Configure>", update_bag_scroll_region)
    bag_canvas.bind("<MouseWheel>", scroll_bag)
    bag_canvas.bind("<Configure>", resize_bag_contents)

    def source_list_text(names):
        """Format berry names as a natural-language list."""
        if len(names) < 2:
            return names[0] if names else ""
        if len(names) == 2:
            return f"{names[0]} or {names[1]}"
        return f"{', '.join(names[:-1])} or {names[-1]}"

    bag_row = 0
    bag_contents.grid_columnconfigure(0, weight=1)
    bag_contents.grid_columnconfigure(1, weight=0)

    def add_bag_row(name_text, quantity_text, tooltip_text):
        """Add an item name and a separate right-aligned quantity."""
        name_label = tk.Label(
            bag_contents,
            text=name_text,
            background="#73C5A4",
            anchor="w",
            justify="left",
        )
        name_label.grid(row=bag_row, column=0, sticky="ew", padx=(2, 0))
        quantity_label = tk.Label(
            bag_contents,
            text=quantity_text,
            background="#73C5A4",
            anchor="e",
            justify="right",
        )
        quantity_label.grid(row=bag_row, column=1, sticky="e", padx=(2, 4))
        bag_row_labels.append(name_label)
        for label in (name_label, quantity_label):
            bind_tree_tooltip(label, tooltip_text)
            label.bind("<MouseWheel>", scroll_bag)

    for section_name in ("Pokéblocks", "Berries"):
        section_label = tk.Label(
            bag_contents,
            text=section_name,
            font=("TkDefaultFont", 9, "bold"),
            background="#73C5A4",
            anchor="w",
        )
        section_label.grid(
            row=bag_row,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=2,
            pady=(3, 1),
        )
        section_label.bind("<MouseWheel>", scroll_bag)
        bag_row += 1
        if section_name == "Pokéblocks":
            block_gains = get_pokeblock_gains(bag)
            block_quantities = {
                block_type: bag.get(item_id, 0)
                for item_id, block_type in POKEBLOCK_ITEMS.items()
            }
            for block_type in POKEBLOCK_ITEMS.values():
                quantity = block_quantities[block_type]
                block_gain = block_gains.get(block_type, 0)
                sources = [
                    berry_data[0]
                    for berry_data in BERRY_ITEMS.values()
                    if berry_data[2].replace(".", "") == block_type
                ]
                tooltip_text = (
                    f"(Made from {source_list_text(sources)} Berry)"
                    if sources
                    else None
                )
                add_bag_row(
                    f"{block_type} Pokéblock",
                    f"{f'(+{block_gain})  ' if block_gain else ''}x{quantity}",
                    tooltip_text,
                )
                bag_row += 1
        else:
            for item_id, berry_data in BERRY_ITEMS.items():
                berry, description, block_type, _ = berry_data
                quantity = bag.get(item_id, 0)
                projected_harvest = harvest.get(berry, 0)
                if quantity == 0 and projected_harvest == 0:
                    continue
                tooltip_text = description
                if block_type != "—":
                    normalized_block_type = block_type.replace(".", "")
                    create_text = f"Creates {normalized_block_type} Pokéblock"
                    tooltip_text = (
                        f"{tooltip_text} ({create_text})"
                        if tooltip_text
                        else create_text
                    )
                add_bag_row(
                    f"{berry} Berry",
                    (
                        f"{f'(+{projected_harvest})  ' if projected_harvest else ''}"
                        f"x{quantity}"
                    ),
                    tooltip_text or None,
                )
                bag_row += 1

    quest_frame = tk.LabelFrame(
        root,
        text="Quest Book",
        background="#73C5A4",
        padx=6,
        pady=4,
    )
    quest_frame.grid(
        row=1,
        column=2,
        padx=3,
        pady=(0, 8),
        sticky="nsew",
    )
    quest_frame.grid_columnconfigure(0, weight=1)

    quest_filters = tk.Frame(quest_frame, background="#73C5A4")
    quest_filters.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
    show_main_quests = tk.BooleanVar(root, value=True)
    show_masteries = tk.BooleanVar(root, value=True)
    show_completed_quests = tk.BooleanVar(root, value=False)
    challenge_filter_vars = {
        difficulty: tk.BooleanVar(root, value=difficulty == challenge_difficulty)
        for difficulty in range(len(QUEST_DIFFICULTIES))
    }
    quest_canvas_width = 130
    quest_row_height = 18
    mastery_row_height = 24
    filter_row_height = 16
    mastery_icons = {}
    dex_number_by_name = {name: number for number, name in POKEMON_NAMES.items()}
    quest_canvas = tk.Canvas(
        quest_frame,
        width=quest_canvas_width,
        height=300,
        background="#73C5A4",
        highlightthickness=0,
        borderwidth=0,
    )
    quest_scrollbar = ttk.Scrollbar(
        quest_frame,
        orient="vertical",
        style="Slim.Vertical.TScrollbar",
        command=quest_canvas.yview,
    )
    quest_canvas.configure(yscrollcommand=quest_scrollbar.set)
    quest_canvas.grid(row=3, column=0, sticky="nsew")
    quest_scrollbar.grid(row=3, column=1, sticky="ns")
    quest_frame.grid_rowconfigure(3, weight=1)

    mastery_tooltips = {name: tooltip for _, name, tooltip in POKEMON_MASTERIES}

    def get_mastery_icon(mastery_name):
        """Return the full-size Pokédex icon for a mastery's lead Pokémon."""
        if mastery_name not in mastery_icons:
            lookup_name = mastery_name
            if lookup_name not in dex_number_by_name:
                lookup_name = mastery_tooltips[mastery_name].split(", ")[0]
            mastery_icons[mastery_name] = get_pokemon_icon(
                dex_number_by_name[lookup_name]
            )
        return mastery_icons[mastery_name]

    def update_quest_filter():
        """Render selected quest groups and their completion status."""
        selected_difficulty = next(
            (
                difficulty
                for difficulty, variable in challenge_filter_vars.items()
                if variable.get()
            ),
            None,
        )
        sections = []

        if show_main_quests.get():
            sections.append(
                (
                    "Main Quests",
                    [
                        (
                            title,
                            bool(quest_states[quest_id] & QUEST_COMPLETED_MASK),
                            requirement,
                        )
                        for quest_id, title, requirement in MAIN_QUESTS
                    ],
                )
            )

        if selected_difficulty is not None:
            sections.append(
                (
                    "Challenges",
                    [
                        (
                            title,
                            bool(
                                quest_states[quest_id] & QUEST_COMPLETED_MASK
                                and (
                                    quest_states[quest_id] >> QUEST_DIFFICULTY_SHIFT
                                ) & 0x7
                                >= selected_difficulty
                            ),
                            requirement,
                        )
                        for quest_id, title, requirement in CHALLENGE_QUESTS
                    ],
                )
            )

        if show_masteries.get():
            sections.append(
                (
                    "Pokémon Masteries",
                    [
                        (
                            f"{name} Mastery",
                            bool(
                                quest_states[quest_id] & QUEST_COMPLETED_MASK
                            ),
                            tooltip,
                        )
                        for quest_id, name, tooltip in POKEMON_MASTERIES
                    ],
                )
            )

        visible_sections = [
            (
                title,
                [
                    (name, completed, tooltip)
                    for name, completed, tooltip in entries
                    if show_completed_quests.get() or not completed
                ],
            )
            for title, entries in sections
        ]
        visible_sections = [
            section for section in visible_sections if section[1]
        ]

        quest_canvas.delete("quest_row")
        y = 5
        text_width = quest_canvas_width - 42
        quest_font = tkfont.nametofont("TkDefaultFont")

        for title, entries in visible_sections:
            quest_canvas.create_text(
                8,
                y,
                text=title,
                anchor="nw",
                font=("TkDefaultFont", 9, "bold"),
                tags=("quest_row",),
            )
            y += quest_row_height

            for name, completed, tooltip_text in entries:
                display_name = name
                if quest_font.measure(display_name) > text_width:
                    while (
                        display_name
                        and quest_font.measure(display_name + "...") > text_width
                    ):
                        display_name = display_name[:-1]
                    display_name = display_name.rstrip() + "..."

                is_mastery = name.endswith(" Mastery")
                row_height = (
                    mastery_row_height if is_mastery else quest_row_height
                )

                if is_mastery:
                    mastery_name = name[:-len(" Mastery")]
                    row_icon = (
                        status_icons["Shiny"]
                        if completed
                        else get_mastery_icon(mastery_name)
                    )
                else:
                    row_icon = status_icons["Shiny" if completed else "Seen"]

                quest_canvas.create_image(
                    16,
                    y + row_height // 2,
                    image=row_icon,
                    tags=("quest_row",),
                )
                text_item = quest_canvas.create_text(
                    31,
                    y + row_height // 2,
                    text=display_name,
                    anchor="w",
                    tags=("quest_row",),
                )
                bind_canvas_tooltip(quest_canvas, text_item, tooltip_text)
                y += row_height

            quest_canvas.create_line(
                6,
                y + 2,
                quest_canvas_width - 6,
                y + 2,
                fill="#36745D",
                tags=("quest_row",),
            )
            y += 8

        if not visible_sections:
            quest_canvas.create_text(
                8,
                y,
                text="No quests match the selected filters.",
                anchor="nw",
                tags=("quest_row",),
            )
            y += quest_row_height

        quest_canvas.configure(
            scrollregion=(0, 0, quest_canvas_width, y)
        )
        quest_canvas.yview_moveto(0)

    def get_quest_percentages():
        """Return completion percentages for main, challenge, and mastery quests."""
        main_done = sum(
            bool(quest_states[quest_id] & QUEST_COMPLETED_MASK)
            for quest_id, _, _ in MAIN_QUESTS
        )
        mastery_done = sum(
            bool(quest_states[quest_id] & QUEST_COMPLETED_MASK)
            for quest_id, _, _ in POKEMON_MASTERIES
        )
        challenge_done = [
            sum(
                bool(
                    quest_states[quest_id] & QUEST_COMPLETED_MASK
                    and (quest_states[quest_id] >> QUEST_DIFFICULTY_SHIFT) & 0x7
                    >= difficulty
                )
                for quest_id, _, _ in CHALLENGE_QUESTS
            )
            for difficulty in range(len(QUEST_DIFFICULTIES))
        ]
        return (
            100 * main_done // len(MAIN_QUESTS),
            [100 * done // len(CHALLENGE_QUESTS) for done in challenge_done],
            100 * mastery_done // len(POKEMON_MASTERIES),
        )

    def select_challenge_difficulty(selected):
        """Keep at most one challenge difficulty checked, then refresh the list."""
        if challenge_filter_vars[selected].get():
            for option, variable in challenge_filter_vars.items():
                if option != selected:
                    variable.set(False)
        update_quest_filter()

    main_percent, challenge_percents, mastery_percent = get_quest_percentages()

    def add_quest_filter(row, label, variable, percent, command, indent=0):
        """Add a fixed-height checkbox row with a right-aligned percentage."""
        row_frame = tk.Frame(
            quest_filters,
            background="#73C5A4",
            width=quest_canvas_width,
            height=filter_row_height,
        )
        row_frame.grid(
            row=row, column=0, columnspan=2, padx=(indent, 0), sticky="ew"
        )
        tk.Checkbutton(
            row_frame,
            text=label,
            variable=variable,
            command=command,
            background="#73C5A4",
            activebackground="#73C5A4",
            anchor="w",
            pady=0,
            highlightthickness=0,
        ).place(x=0, rely=0.5, anchor="w")
        if percent is not None:
            tk.Label(
                row_frame,
                text=f"{percent}%",
                background="#73C5A4",
                anchor="e",
                pady=0,
            ).place(relx=1.0, rely=0.5, anchor="e")

    quest_filters.grid_columnconfigure(0, weight=1)
    add_quest_filter(
        0, "Main", show_main_quests, main_percent, update_quest_filter
    )
    tk.Label(
        quest_filters,
        text="Challenges",
        background="#73C5A4",
        anchor="w",
    ).grid(row=1, column=0, columnspan=2, pady=(2, 0), sticky="w")
    for difficulty, label in enumerate(QUEST_DIFFICULTIES):
        add_quest_filter(
            2 + difficulty,
            label,
            challenge_filter_vars[difficulty],
            challenge_percents[difficulty],
            lambda option=difficulty: select_challenge_difficulty(option),
        )
    add_quest_filter(
        6, "PkMn Mastery", show_masteries, mastery_percent, update_quest_filter
    )
    add_quest_filter(
        7, "Show Completed", show_completed_quests, None, update_quest_filter
    )
    quest_filters.grid_rowconfigure(6, pad=8)


    root.update_idletasks()
    update_quest_filter()

    def animate_sprites(frame_index=0):
        """Advance all two-frame tree animations every half second."""
        next_frame = 1 - frame_index
        for canvas, image_id, frames in animation_items:
            canvas.itemconfigure(image_id, image=frames[next_frame % len(frames)])
        if any(len(frames) > 1 for _, _, frames in animation_items):
            root.after(500, animate_sprites, next_frame)

    if any(len(frames) > 1 for _, _, frames in animation_items):
        root.after(500, animate_sprites, 0)
    root.mainloop()


def main():
    """Print save info, quest, Pokédex, berry, and Pokéblock status."""
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) != 2:
        print("Drag an Emerald Rogue .srm/.sav file onto this script.")
        input("\nPress Enter to exit...")
        return

    save_path = Path(sys.argv[1])

    if not save_path.is_file():
        print(f"File not found: {save_path}")
        input("\nPress Enter to exit...")
        return

    try:
        (
            block,
            save_counter,
            encryption_key,
            storage,
            saveblock2,
        ) = read_save_blocks(save_path)

        if len(block) < DEX_CAUGHT_OFFSET + DEX_SIZE:
            raise ValueError("SaveBlock1 is smaller than expected.")

        (
            challenge_difficulty,
            difficulty_name,
            play_time,
        ) = print_save_info(saveblock2, storage)
        trainer_name = decode_trainer_name(saveblock2)
        bank_money, wallet_money = read_money(block, encryption_key, storage)
        hub_name = get_hub_name(block, saveblock2)
        quest_states = read_quest_states(storage)
        print_quest_progress(storage)

        seen = block[DEX_SEEN_OFFSET:DEX_SEEN_OFFSET + DEX_SIZE]
        caught = block[DEX_CAUGHT_OFFSET:DEX_CAUGHT_OFFSET + DEX_SIZE]

        names = POKEMON_NAMES
        plots = read_berry_plots(block)
        bag = decode_bag(block, encryption_key)
        harvest = get_berry_harvest(plots)
        print_berry_and_pokeblock_info(bag, plots, harvest)

        missing = []
        caught_shiny = []
        for dex_number in range(1, NUM_POKEMON + 1):
            species_id = national_dex_to_species_id(dex_number)
            name = names.get(dex_number, f"Pokémon #{dex_number}")
            status = get_pokedex_status(seen, caught, species_id)
            if status == "Shiny":
                caught_shiny.append((dex_number, name))
            elif status != "Caught":
                is_seen = status == "Seen"
                missing.append((dex_number, name, is_seen))

        print()
        print("=" * 55)
        print(f" Uncaught Pokémon: {len(missing)}")
        print("=" * 55)

        for dex_number, name, is_seen in missing:
            status = "Seen" if is_seen else "Not seen"
            print(f"#{dex_number:03d} {name:<20} [{status}]")

        print()
        print("=" * 55)
        print(f" Caught Shiny Pokémon: {len(caught_shiny)}")
        print("=" * 55)
        for dex_number, name in caught_shiny:
            print(f"#{dex_number:03d} {name}")

        print("=" * 55)
        print(f"Save: {save_path.name}")
        print(f"Save counter used: {save_counter}")
        print()

        show_berry_plots(
            plots,
            bag,
            harvest,
            seen,
            caught,
            quest_states,
            challenge_difficulty,
            trainer_name,
            difficulty_name,
            play_time,
            bank_money,
            wallet_money,
            hub_name,
        )

    except Exception as e:
        print(f"\nERROR: {e}")

    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
