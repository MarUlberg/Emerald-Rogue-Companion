# Pokémon Emerald Rogue Save Structure Reference

> **Disclaimer:** This is unofficial documentation written by AI. It is likely
> to contain wrong information. Verify offsets, layouts, and values against
> your own saves and the game source before relying on them.

## 1. Purpose and scope

This document describes the organization and interpretation of Pokémon
Emerald Rogue save data for save readers and related tools. It is a structural
reference, not a report of the contents of any individual save.

Emerald Rogue builds and revisions can change block layouts, item tables, and
feature-specific data. Offsets below are relative to a reconstructed logical
save block unless explicitly described as raw-file offsets. Treat every
offset as belonging to a particular game revision until it has been checked
against that revision's source or validated against representative saves.

No inventory quantities, save counters, individual Pokédex states, or
particular planted berry species are specified here; those are mutable
save data.

## 2. Physical save organization

The common GBA SRAM container used by the supported Emerald Rogue 2.0.x
layout is 128 KiB:

| Property | Value |
|---|---:|
| File size | `0x20000` bytes |
| Sector size | `0x1000` (4096) bytes |
| Sector count | 32 |
| Sector payload | `0xFF4` (4084) bytes |
| Sector metadata | 12 bytes |

Each sector consists of its payload followed by metadata:

| Sector-relative offset | Size | Meaning |
|---:|---:|---|
| `0xFF4` | 2 | Sector ID, little-endian |
| `0xFF6` | 2 | Sector checksum |
| `0xFF8` | 4 | Signature |
| `0xFFC` | 4 | Save counter, little-endian |

The file normally contains rotating or alternating copies of saved data.
Do not identify the current save by physical sector position alone. Group
sectors by save counter, verify that the expected IDs form a complete logical
set, and select the newest complete set for that game revision. Pair any
separate SaveBlock2 sector with SaveBlock1 sectors from the same counter.
If counters can wrap in the target format, compare them with wrap-aware
generation ordering rather than ordinary integer `max()`.

For the 2.0.x layout implemented by the companion parser, sector IDs `1–4`
are the four SaveBlock1 payload parts and ID `0` is the associated
SaveBlock2 payload:

| Sector ID | Logical data |
|---:|---|
| 0 | SaveBlock2 |
| 1 | SaveBlock1 bytes `0x0000–0x0FF3` |
| 2 | SaveBlock1 bytes `0x0FF4–0x1FE7` |
| 3 | SaveBlock1 bytes `0x1FE8–0x2FDB` |
| 4 | SaveBlock1 bytes `0x2FDC–0x3FCF` |

Sector IDs `5–13` hold the Pokémon Storage structure and its trailing Rogue
save data. Their payloads also form a logical byte stream in sector-ID order:

| Sector ID | Pokémon Storage bytes |
|---:|---|
| 5 | `0x0000–0x0FF3` |
| 6 | `0x0FF4–0x1FE7` |
| 7 | `0x1FE8–0x2FDB` |
| 8 | `0x2FDC–0x3FCF` |
| 9 | `0x3FD0–0x4FC3` |
| 10 | `0x4FC4–0x5FB7` |
| 11 | `0x5FB8–0x6FAB` |
| 12 | `0x6FAC–0x7F9F` |
| 13 | `0x7FA0–0x8F93` |

The block reconstruction concatenates the 4084-byte payloads for IDs 1, 2,
3, and 4 in ID order. This produces a `0x3FD0`-byte logical SaveBlock1.
Concatenate IDs 5–13 in the same way when interpreting Pokémon Storage and
the Rogue data appended to it. Sector-ID assignments and block sizes are
format/revision details, not universal assumptions for every Emerald Rogue
build.

### Raw sector address formula

For a payload byte at logical SaveBlock1 offset `x`, the corresponding raw
file location depends on which logical sector contains it:

```text
logical sector part = x // 0xFF4
offset within payload = x % 0xFF4
raw file offset =
    physical sector file offset + offset within payload
```

First determine the physical sector that matches the desired logical
SaveBlock1 part and counter. Never assume that logical offset `x` is also raw
file offset `x`.

## 3. Logical save blocks

### SaveBlock1

SaveBlock1 contains mutable world and player data. The companion parser
reconstructs it from four sectors as described above. Known fields in the
2.0.x layout include bag slots, berry-tree records, and Pokédex bitfields.

The EX v2.0-derived source profile names the following SaveBlock1 regions.
These are logical offsets and are useful as a structural map; confirm any
field before applying it to a different build.

| SaveBlock1 offset | Field / purpose |
|---:|---|
| `0x000C` | Continue-game warp |
| `0x0014` | Dynamic warp |
| `0x001C` | Last-heal-location warp |
| `0x0024` | Escape warp |
| `0x002C` | Saved music |
| `0x002E` | Weather and weather-cycle state |
| `0x0030` | Flash level |
| `0x0032` | Map layout ID |
| `0x0034` | Map-view tile data |
| `0x0234` | Party count |
| `0x0238` | Party Pokémon records |
| `0x0490` | Money (source profile; companion parser profile `0x04A8`) |
| `0x0494` | Bag sort mode and capacity upgrades |
| `0x0498` | PC item slots |
| `0x0560` | Bag pockets (source profile) |
| `0x09BC` | Berry Blender records and following object/template metadata |
| `0x0A30` | Object events |
| `0x0C70` | Object-event templates |
| `0x1270` | Game flags |
| `0x139C` | Game variables |
| `0x159C` | Game statistics |
| `0x169C` | Berry-tree array |
| `0x1A9C` | Secret-base records |
| `0x271C` | Player-room decorations |
| `0x2728` | Player-room decoration positions |
| `0x27CC` | TV-show records |
| `0x2B50` | PokéNews records |
| `0x2B90` | Outbreak state |
| `0x2BB0` | Easy Chat profile and battle-result words |
| `0x2BE0` | Mail records |
| `0x2E20` | Unlocked trendy-saying bitfield |
| `0x2E28` | Old Man state |
| `0x2E64` | Dewford trend records |
| `0x3030` | Day Care data |
| `0x3150` | Link-battle records |

### SaveBlock2

SaveBlock2 contains player configuration and other global state. Its
encryption key is used to encode bag quantities. The key's offset can differ
between source revisions and shipped builds; identify it for the exact target
before decoding inventory. The companion parser's current profile reads a
32-bit little-endian key at `SaveBlock2 + 0x4C`.

Other EX v2.0-derived source layouts place the encryption key at `+0xAC`.
Do not use either key offset without matching it to the target executable and
save layout.

In that source profile, SaveBlock2 also includes the player name at `+0x00`,
gender at `+0x08`, trainer ID at `+0x0A`, play time at `+0x0E`, configuration
options beginning at `+0x13`, a Pokédex structure at `+0x18`, local-time
offset at `+0x98`, and last berry-tree update time at `+0xA0`.

Play time is stored at `SaveBlock2 + 0x0E` as a little-endian 16-bit hour
count followed by one-byte minutes, seconds, and VBlank count. The companion
prints the hour, minute, and second fields as `H:MM:SS`.

Offsets are always relative to the beginning of the logical block, not the
beginning of a physical SRAM sector.

### Live values vs. hub backup values

Emerald Rogue keeps two sets of bag, money, and play-time data. The live values
describe whatever the player is currently doing (the hub or an adventure). The
hub backup values are a snapshot of the hub state, so the hub's bag and money
remain readable while the save was written mid-adventure. Compared against a
hub save and a mid-adventure save of the same file (companion parser profile):

| Value | Live location | Hub backup location |
|---|---|---|
| Bag | SaveBlock1 `+0x578`, 450 slots, quantity XOR key | Storage stream `+0x7089`, 450 slots, **plain** quantity |
| Money | SaveBlock1 `+0x4A8` (`uint32`), XOR full 32-bit key | Storage stream `+0x7899` (`uint32`), **plain** |
| Play time | SaveBlock2 `+0x0E` (`uint16` hours, minutes, seconds, VBlanks) | Not found |

Details:

- The storage stream is the concatenation of the nine Pokémon Storage sectors
  (IDs 5–13) for the chosen save counter, the same stream that holds the Rogue
  save block at `+0x5DC4`.
- Hub backup bag slots use the same four-byte layout as live slots (`uint16`
  item ID, `uint16` quantity) but the quantity is not encrypted. Slot `i` is at
  `0x7089 + 4 * i`; the array ends at `0x7791`.
- Hub backup money is 4 bytes at `0x7899`, `0x108` bytes after the end of the
  backup bag. It is unaligned.
- The live money offset `+0x4A8` is the source profile's `0x490` shifted by
  `0x18`, the same shift as the bag (`0x578` vs. `0x560`).
- Live values are the hub values when the save was written in the hub. Mid
  adventure they are the run's bag, money, and play time. Live play time then
  counts the current adventure only, as `H:MM:SS`.
- The backup is a snapshot taken when the adventure begins, so it excludes
  later hub changes such as rewards earned on exit. It exists in hub saves too,
  and then may not match the live values, so use it only when the save is known
  to be mid-adventure.
- No copy of the hub play time was found anywhere in the file. Neither the
  `H:MM:SS` form, raw seconds/minutes, nor frame counts matched, plain or XORed
  with either key.

### Hub name and location

- **Hub name:** SaveBlock2 `+0xEE4`, a Gen 3 text string terminated by `0xFF`
  (up to 16 bytes observed). Main Save holds `End Town`; the test save holds
  `TUA`. The companion shows it in "Trainer <name> is resting in <hub name>."
- **Saved location:** SaveBlock1 `+0x04` holds the map group and map number
  (one signed byte each). The companion currently treats map group `2` as the
  hub. Findings so far indicate that group 2 appears to indicate the hub, but
  more testing is required. Hub saves seen: group 2 with map numbers 3, 4, 5,
  6, 8, and 13; the one mid-adventure save was at `(7, 0)`. Saves from other
  adventure maps may also use group 2 and be misclassified.
- **Map group 6 (adventure map):** map `(6, 0)` (layout 103) is confirmed as
  the **Adventure Map**, the area between routes. The player position changes
  within it as the run progresses. Other group 6 maps seen mid-run were
  `(6, 32)` and `(6, 38)`; their purpose is not yet determined. Treat group 6
  as a run location, not the hub.
- **Map group 7 (routes/events):** maps seen in saves made inside a route or
  event include `(7, 0)`, `(7, 3)`, `(7, 4)`, `(7, 12)`, and `(7, 23)`.
- **Confirmed locations:**

  | Map (group, num) | Layout | Location |
  |---|---:|---|
  | `(6, 0)` | 103 | Adventure Map (between routes) |
  | `(7, 23)` | 70 | Gym |

- The continue, dynamic, and escape warps (`+0x0C`, `+0x14`, `+0x1C`) pointed
  to the hub in every save, including the adventure one, so they do not
  indicate hub vs. adventure.

Validation example (same file saved in the hub, then mid adventure):

| Value | Hub save | Mid-adventure save |
|---|---:|---:|
| Live money | 86,440 | 149,840 |
| Hub backup money | 82,440 | 82,440 |
| Live play time | 302:36:35 | 1:41:06 |
| Live bag | 86 distinct items | different run bag |
| Hub backup bag | 86 items, same as its live bag | 86 items, identical to the hub save's live bag |

### Layout-profile differences

The companion parser profile and the EX v2.0-derived source profile differ:

| Field | Companion parser profile | EX v2.0-derived source profile |
|---|---|---|
| Bag slots | SaveBlock1 `+0x578` | SaveBlock1 `+0x560` |
| Encryption key | SaveBlock2 `+0x4C` | SaveBlock2 `+0xAC` |
| Pokédex | SaveBlock1 `+0x30B4` / `+0x3173` | SaveBlock2 `+0x18` structure |

These are alternative layout descriptions, not offsets to combine. Resolve
the target revision/profile before decoding fields; do not silently fall
back from one set of offsets to another.

### Rogue quest progress

In the v2.0.1a-EX save profile, the `RogueSaveBlock` begins in the logical
Pokémon Storage stream at `+0x5DC4`. This is build-specific: Rogue data is
appended after the ten usable Pokémon boxes, and its location depends on the
target's `PokemonStorage` definition. Do not apply this offset to a different
build without verifying its storage layout.

The serialized Rogue block begins with a six-byte header followed by the
quest-state array's two-byte element count:

| Pokémon Storage offset | Size | Field |
|---:|---:|---|
| `0x5DC4` | 2 | Rogue save version |
| `0x5DC6` | 1 | Rogue block format |
| `0x5DC7` | 2 | Secret ID / block-validity marker |
| `0x5DC9` | 1 | Rogue game version |
| `0x5DCA` | 2 | Quest-state array length |
| `0x5DCC` | variable | Quest-state records |

Each quest-state record occupies eight bytes in the v2.0.1a-EX serialized
Rogue block. The source structure's bitfields total 34 bits (`16 + 3 + 3 +
12`), so the record is larger than the four-byte word containing the fields
used for completion and difficulty. The companion reads that first
little-endian 32-bit word and advances eight bytes to the next record. For
the quest's numeric `QUEST_ID` value `q` from the matching game build:

```text
record offset = 0x5DCC + (8 * q)
meaningful state word = record offset + 0x00
next record = record offset + 0x08
```

| First-word bit(s) | Meaning |
|---:|---|
| 0–15 | State flags |
| 0 | Unlocked |
| 1 | Active |
| 2 | Pinned |
| 3 | Pending rewards |
| 4 | Newly unlocked |
| 5 | Completed (`HAS_COMPLETE`, mask `0x0020` in the low 16-bit flags) |
| 16–18 | Highest completed difficulty |
| 19–21 | Highest collected-reward difficulty |

The record's remaining four bytes are part of the wider C bitfield structure;
they are not another quest record. Completion is set when the low 16-bit
state-flags field has mask `0x0020` set; the other state flags and difficulty
fields are separate and should not be mistaken for completion.
The quest-ID-to-title ordering is generated from the quest data and may vary
by game revision or build options. Use the `QUEST_ID` enumeration from the
matching build to map a title to `q`; the progress notes for a save identify
which quests are complete but do not define that enumeration.

The companion's console report uses the 198-entry Expansion v2.0 quest
catalog. Its generated ID order is not the same as the menu/report grouping:
IDs `0–39` are the initial main quests; ID `40` is Regional Style; IDs `41–50`
are region challenges; ID `51` is Type Master; IDs `52–69` are type
challenges; IDs `70–94` are the other challenges; and IDs `95–197` are Pokémon
masteries. The source generator processes included quest groups before each
file's local group, which places region and type quests before the local
default-challenge group.

Regular quests and Pokémon masteries have one completion column; challenge
rows have one column per preset difficulty. Since the save stores only the
highest completed challenge difficulty, the report marks each preset up to
and including that level. Regional Style and Type Master are summary quests:
their completion flag is recorded at their own IDs, independently of the
individual region or type challenge flags. The report rejects save versions
or quest counts that do not match this catalog rather than displaying
potentially misaligned quest names.

For the calibrated v2.0.1a-EX save profile, the serialized difficulty
configuration begins at Pokémon Storage offset `0x6D26` (`RogueSaveBlock +
0x1562`). Its two arrays are prefixed by 16-bit element counts: three toggle
bytes are followed by the range-value array. The difficulty preset is range
value index `6`: `0` Easy, `1` Average, `2` Hard, `3` Brutal, or `4` Custom.
The companion validates the toggle-array length and accepts the known range
array lengths of 7 and 9 before displaying this field. The play-time and
difficulty fields are read from the SaveBlock2 and Pokémon Storage sectors
matching the same save counter as SaveBlock1 and quest progress.

For a raw-file address, first select the Pokémon Storage sectors belonging to
the same complete save generation. For a logical Pokémon Storage offset `x`:

```text
sector ID = 5 + (x // 0xFF4)
offset within sector payload = x % 0xFF4
raw file offset = physical sector file offset + offset within payload
```

For example, quest ID `0`'s state word starts at Pokémon Storage offset
`0x5DCC`, which maps to sector ID `10` at payload offset `0xE08`. Quest ID `1`
starts eight bytes later, at `0x5DD4`.

This is a serialized save structure, not the in-memory C structure's
`sizeof` or padding. Its header and quest-array length should be checked
before reading records. In save versions that serialize `lastKnownNumSpecies`
before the quest array, the array count and records are shifted by two bytes;
verify the version-specific serialization before applying these offsets.

## 4. Bag item slots

The bag is stored as an array of four-byte item slots. In the companion
parser's current 2.0.x profile, the array starts at `SaveBlock1 + 0x578` and
contains 450 slots.

| Slot-relative offset | Size | Field |
|---:|---:|---|
| `+0x00` | 2 | Item ID (`uint16`, little-endian) |
| `+0x02` | 2 | Encrypted quantity (`uint16`, little-endian) |

For slot index `i`:

```text
slot offset = 0x578 + 4 * i
0 <= i < 450
```

The quantity uses the low 16 bits of the SaveBlock2 encryption key:

```python
quantity = encrypted_quantity ^ (encryption_key & 0xFFFF)
```

An item ID of zero denotes an unused slot. Combine duplicate item IDs when
reporting total quantities. Do not hardcode quantities; item names and item
categories are game definitions and may be kept in a revision-appropriate
lookup table.

### Item-ID tables

Item IDs are identifiers, not quantities. They must be interpreted using the
item table for the target build. The companion's current table assigns berry
items in the range `525–592` and Pokéblocks in the range `847–871`; these
numbers are revision-specific and should not be applied to another build
without checking its item definitions. Some EX v2.0-derived source layouts
place the bag array at `SaveBlock1 + 0x560`; that is not interchangeable with
the companion parser profile's `0x578`.

Berry-tree records use a compact berry type byte, not the bag's 16-bit item
ID. Convert between the two using the berry definitions for the target game;
do not treat the values as interchangeable.

## 5. Pokédex status bitfields

The calibrated v2.0.1a-EX profile stores two 191-byte bit planes in
SaveBlock1:

| Field | SaveBlock1 offset | Length |
|---|---:|---:|
| State bit 0 | `0x30B4` | 191 bytes |
| State bit 1 | `0x3173` | 191 bytes |

Together, the planes encode each species' Pokédex state: `00` undiscovered,
`01` seen, `10` caught, and `11` caught shiny. A caught species has its
state-bit-1 flag set; when both bits are set, display it as Shiny (Caught
Shiny), not as an uncaught Pokémon.
The bit index is the build's internal species ID, not its National Dex number:

```python
byte_index = species_id // 8
bit_index = species_id % 8
is_set = bool(bit_plane[byte_index] & (1 << bit_index))
```

For this build, National Dex numbers `1–905` use the same internal species ID.
Generation IX species start at internal ID `1289`; form variants inserted
among those IDs create the following offset ranges:

| First National Dex number | Add to National Dex number |
|---:|---:|
| 906 | 383 |
| 917 | 384 |
| 926 | 385 |
| 932 | 388 |
| 965 | 389 |
| 979 | 391 |
| 983 | 392 |
| 1000 | 393 |
| 1009 | 397 |
| 1013 | 398 |
| 1014 | 399 |
| 1018 | 407 |

Use the most recent starting number not greater than the National Dex number
to select its offset. These offsets and the two bit-plane locations are
revision-specific; do not apply them to other Emerald Rogue builds without
calibration.

## 6. Berry-tree array

The known EX v2.0-derived SaveBlock1 layout places the berry-tree array at
`SaveBlock1 + 0x169C`. It contains 128 indexed records. The record fields
occupy six bytes; the array span and following SaveBlock1 field placement
indicate an eight-byte record stride, with two trailing bytes not defined by
the `BerryTree` fields.

```text
tree record offset = 0x169C + (tree_id * 8)
```

IDs index the global array. Which IDs correspond to a visible tree or farm
plot depends on the map/object using that ID. Do not assume plot number equals
tree ID or that every map uses the same subset.

### Record layout

| Record offset | Size | Field |
|---:|---:|---|
| `+0x00` | 1 | Berry type |
| `+0x01` | 1 | Growth stage and stop-growth flag |
| `+0x02` | 2 | Minutes until next stage, little-endian |
| `+0x04` | 1 | Berry yield |
| `+0x05` | 1 | Regrowth and watering flags |
| `+0x06` | 2 | Unspecified trailing bytes / padding |

### Stage and growth-control byte (`+0x01`)

```text
bit 7       bits 6..0
stopGrowth  stage
```

```python
stage = status & 0x7F
stop_growth = bool(status & 0x80)
```

Known stage constants:

| Value | Meaning |
|---:|---|
| 0 | No berry |
| 1 | Planted |
| 2 | Sprouted |
| 3 | Taller |
| 4 | Flowering |
| 5 | Berries |
| 255 | Sparkling special stage |

The sparkling constant is a special stage value, not an ordinary value in the
seven-bit stage field. Handle it explicitly if the target build stores it
directly.

### Regrowth and watering byte (`+0x05`)

| Bits | Meaning | Extraction |
|---|---|---|
| 0–3 | Regrowth count | `flags & 0x0F` |
| 4 | Watered during stage 1 | `bool(flags & 0x10)` |
| 5 | Watered during stage 2 | `bool(flags & 0x20)` |
| 6 | Watered during stage 3 | `bool(flags & 0x40)` |
| 7 | Watered during stage 4 | `bool(flags & 0x80)` |

The yield byte stores the tree's calculated yield when the game has reached
the berry-bearing stage. The companion's future-harvest projection is a
separate estimate: it counts every recognized planted tree, regardless of
stage, at 9 berries per plant. That fixed estimate is a tool rule, not a
value stored in the tree record. The time field is a countdown/state value;
it is not a wall-clock timestamp.

The companion reports the estimated harvest beside each berry's current bag
quantity, including berries with zero current quantity when a planted tree
will produce them. The Pokéblock bonus is calculated independently from
current bag contents only: each full set of 70 of an individual berry
corresponds to 30 Pokéblocks of that berry's recipe. Future plot harvest is
not included in the Pokéblock bonus.

### Growth timing

In v2.0.1a-EX, berry growth is driven by progress through an adventure, not by
the real-time clock or play time. Every time the player enters a room from the
adventure-path overview (route, rest stop, gym/boss, and so on), every planted
tree's countdown is reduced by **120 minutes**. Hub trees and in-run trees
share the same array, so they all advance together.

- The `+0x02` countdown is refilled with the berry's stage length (see the
  Growth Rate column) each time a stage completes; the berry-bearing stage is
  four times that length.
- A tree needs four stage changes to bear berries. Total minutes to ripen is
  `4 × stage length` (Oran: 4 × 180 = 720 minutes, i.e. 6 room entries).
- Wins, losses, forfeits, rival/gym results, difficulty and game mode have no
  direct effect. Game mode only matters indirectly through how many rooms the
  adventure path contains (the first Gauntlet path is longer than later ones).
- Returning to the overview, starting a run and returning to the hub do not
  grow berries.
- Trees with `stop_growth` set do not advance.

Observed in saves (hub trees at stage 1; Watmel/Durin stage length 1080 and
Starf 1440): the countdown fell by exactly 120 per room entered, unchanged by
defeating the gym or rival, and an unvisited ("skipped") map node did not
count.

| Rooms entered | Watmel / Durin | Starf |
|---:|---:|---:|
| 1 | 960 | 1320 |
| 2 | 840 | 1200 |
| 3 | 720 | 1080 |
| 4 | 600 | 960 |
| 5 | 480 | 840 |
| 6 | 360 | 720 |
| 7 | 240 | 600 |

Source reference: `BerryTreeTimeUpdate(120)` in `Rogue_OnSetWarpData`
(`rogue_controller.c`) of `lbsbezerra/pokeemerald-rogue-improved-graphics`.
Pokabbie's older public `vanilla`/`expansion` branches instead call
`BerryTreeTimeUpdate(600)` after each boss win, so this value is
build-specific.

### Farming-plot ID distinction

Berry-tree IDs are array indices, not plot labels. In the documented
four-plot layout, the farm's 20 slots map to these array indices:

```text
Plot 1: 92, 93, 94, 95, 96
Plot 2: 77, 78, 79, 80, 81
Plot 3: 87, 88, 89, 90, 91
Plot 4: 82, 83, 84, 85, 86
```

This mapping is a map/build definition, not a property of the `BerryTree`
record itself. Other berry-tree objects may use different IDs. Verify the
mapping against the target game's hub/farm map before using it in a parser.

### Berry definitions reference

The source profile below is reproduced from the berry lookup table used by the
companion reference set. It maps the compact berry ID stored in the
`BerryTree` record's `+0x00` byte to the corresponding species, Pokéblock
recipe, sprite asset, and classification. Berry IDs and berry/item
definitions are revision-specific; confirm them against the target build before
using this table as a static definition for another release.

| Item ID | Berry ID | Berry | Tooltip | Growth Rate (min/stage) | Pokéblock | Sprite | Type | Unlock requirement |
|---:|---:|---|---|---:|---|---|---|---|
| 525 | 1 | Cheri | Cures paralysis. | 180 | Electric | Cheri | Type |  |
| 526 | 2 | Chesto | Cures sleep. | 180 | Psychic | Chesto | Type |  |
| 527 | 3 | Pecha | Cures poison. | 180 | Poison | Pecha | Type |  |
| 528 | 4 | Rawst | Cures a burn. | 180 | Fire | Rawst | Type |  |
| 529 | 5 | Aspear | Cures freezing. | 180 | Ice | Aspear | Type |  |
| 530 | 6 | Leppa | Restores 10 PP to a move when its PP reaches 0. | 240 | Flying | Leppa | Type |  |
| 531 | 7 | Oran | Restores 10 HP when the holder's HP is low. | 180 | HP | Oran | Stat |  |
| 532 | 8 | Persim | Cures confusion. | 180 | Normal | Persim | Type |  |
| 533 | 9 | Lum | Cures any major status condition and confusion. | 720 | Normal | Lum | Type |  |
| 534 | 10 | Sitrus | Restores 25% of the holder's max HP when HP is low. | 360 | HP | Sitrus | Stat |  |
| 535 | 11 | Figy | Restores 1/3 HP when low. | 360 | Bug | Figy | Type |  |
| 536 | 12 | Wiki | Restores 1/3 HP when low. | 360 | Rock | Wiki | Type |  |
| 537 | 13 | Mago | Restores 1/3 HP when low. | 360 | Ground | Mago | Type |  |
| 538 | 14 | Aguav | Restores 1/3 HP when low. | 360 | Ice | Aguav | Type |  |
| 539 | 15 | Iapapa | Restores 1/3 HP when low. | 360 | Grass | Iapapa | Type |  |
| 540 | 16 | Razz |  | 60 | Fire | Razz | Type |  |
| 541 | 17 | Bluk |  | 60 | Water | Razz | Type |  |
| 542 | 18 | Nanab |  | 60 | Flying | Mago | Type |  |
| 543 | 19 | Wepear |  | 60 | Psychic | Wepear | Type |  |
| 544 | 20 | Pinap |  | 60 | Electric | Iapapa | Type |  |
| 545 | 21 | Pomeg | Lowers HP EVs by 10. | 180 | HP | Pomeg | Stat |  |
| 546 | 22 | Kelpsy | Lowers Attack EVs by 10. | 180 | ATK | Kelpsy | Stat |  |
| 547 | 23 | Qualot | Lowers Defense EVs by 10. | 180 | DEF | Wepear | Stat |  |
| 548 | 24 | Hondew | Lowers Sp. Atk EVs by 10. | 180 | SP.ATK | Hondew | Stat |  |
| 549 | 25 | Grepa | Lowers Sp. Def EVs by 10. | 180 | SP.DEF | Grepa | Stat |  |
| 550 | 26 | Tamato | Lowers Speed EVs by 10. | 360 | SPEED | Tamato | Stat |  |
| 551 | 27 | Cornn |  | 360 | Dark | Cornn | Type |  |
| 552 | 28 | Magost |  | 360 | Steel | Pomeg | Type |  |
| 553 | 29 | Rabuta |  | 360 | Fighting | Rabuta | Type |  |
| 554 | 30 | Nomel |  | 360 | Ghost | Nomel | Type |  |
| 555 | 31 | Spelon |  | 1080 | Rock | Spelon | Type |  |
| 556 | 32 | Pamtree |  | 1080 | Dragon | Pamtre | Type |  |
| 557 | 33 | Watmel |  | 1080 | Bug | Rabuta | Type |  |
| 558 | 34 | Durin |  | 1080 | Grass | Durin | Type |  |
| 559 | 35 | Belue |  | 1080 | Water | Hondew | Type |  |
| 560 | 36 | Chilan | Weakens a super-effective Normal-type attack. | 1080 | Normal | Grepa | Type | Normal Master |
| 561 | 37 | Occa | Weakens a super-effective Fire-type attack. | 1080 | Fire | Occa | Type | Fire Master |
| 562 | 38 | Passho | Weakens a super-effective Water-type attack. | 1080 | Water | Cornn | Type | Water Master |
| 563 | 39 | Wacan | Weakens a super-effective Electric-type attack. | 1080 | Electric | Razz | Type | Electric Master |
| 564 | 40 | Rindo | Weakens a super-effective Grass-type attack. | 1080 | Grass | Tamato | Type | Grass Master |
| 565 | 41 | Yache | Weakens a super-effective Ice-type attack. | 1080 | Ice | Yache | Type | Ice Master |
| 566 | 42 | Chople | Weakens a super-effective Fighting-type attack. | 1080 | Fighting | Chople | Type | Fighting Master |
| 567 | 43 | Kebia | Weakens a super-effective Poison-type attack. | 1080 | Poison | Kebia | Type | Poison Master |
| 568 | 44 | Shuca | Weakens a super-effective Ground-type attack. | 1080 | Ground | Shuca | Type | Ground Master |
| 569 | 45 | Coba | Weakens a super-effective Flying-type attack. | 1080 | Flying | Rawst | Type | Flying Master |
| 570 | 46 | Payapa | Weakens a super-effective Psychic-type attack. | 1080 | Psychic | Payapa | Type | Psychic Master |
| 571 | 47 | Tanga | Weakens a super-effective Bug-type attack. | 1080 | Bug | Tanga | Type | Bug Master |
| 572 | 48 | Charti | Weakens a super-effective Rock-type attack. | 1080 | Rock | Lansat | Type | Rock Master |
| 573 | 49 | Kasib | Weakens a super-effective Ghost-type attack. | 1080 | Ghost | Kasib | Type | Ghost Master |
| 574 | 50 | Haban | Weakens a super-effective Dragon-type attack. | 1080 | Dragon | Haban | Type | Dragon Master |
| 575 | 51 | Colbur | Weakens a super-effective Dark-type attack. | 1080 | Dark | Colbur | Type | Dark Master |
| 576 | 52 | Babiri | Weakens a super-effective Steel-type attack. | 1080 | Steel | Liechi | Type | Steel Master |
| 577 | 53 | Roseli | Weakens a super-effective Fairy-type attack. | 1080 | Fairy | Roseli | Type | Fairy Master |
| 578 | 54 | Liechi | Raises Attack by one stage when HP is low. | 1440 | ATK | Liechi | Stat |  |
| 579 | 55 | Ganlon | Raises Defense by one stage when HP is low. | 1440 | DEF | Hondew | Stat |  |
| 580 | 56 | Salac | Raises Speed by one stage when HP is low. | 1440 | SPEED | Aguav | Stat |  |
| 581 | 57 | Petaya | Raises Sp. Atk by one stage when HP is low. | 1440 | SP.ATK | Pomeg | Stat |  |
| 582 | 58 | Apicot | Raises Sp. Def by one stage when HP is low. | 1440 | SP.DEF | Grepa | Stat |  |
| 583 | 59 | Lansat | Raises critical-hit ratio when HP is low. | 1440 | Ground | Lansat | Type |  |
| 584 | 60 | Starf | Sharply raises one random stat when HP is low. | 1440 | SHINY | Cornn | Shiny |  |
| 585 | 61 | Enigma | Restores HP when the holder is hit by a super-effective attack. | 1440 | — | Durin | — |  |
| 586 | 62 | Micle | Raises accuracy of the holder's next move when HP is low. | 1440 | HP | Micle | Stat |  |
| 587 | 63 | Custap | Allows the holder to move first when HP is low. | 1440 | SPEED | Custap | Stat |  |
| 588 | 64 | Jaboca | Damages an attacker that hits the holder with a physical move. | 1440 | ATK | Jaboca | Stat |  |
| 589 | 65 | Rowap | Damages an attacker that hits the holder with a special move. | 1440 | SP.ATK | Rowap | Stat |  |
| 590 | 66 | Kee | Raises Defense when the holder is hit by a physical attack. | 1440 | Fairy | Pecha | Type |  |
| 591 | 67 | Maranga | Raises Sp. Def when the holder is hit by a special attack. | 1440 | SP.DEF | Occa | Stat |  |
| 599 | 75 | Enigma |  |  | — |  | — |  |

Growth Rate is the minutes per growth stage (`stageDuration × 60`), taken from
the `berry.c` table of the v2.0.1a EX source fork
(`lbsbezerra/pokeemerald-rogue-improved-graphics`); it is the value the tree's
`+0x02` countdown is reset to at each stage (the berry-bearing stage is four
times longer). Growth advances 120 minutes per room entered; see "Growth
timing" above. The blank duplicate Enigma row (ID 75) has no confirmed value.

This is a source-derived reference table, not an absolute definition for every
release. Older data sets may include legacy rows or duplicate entries; treat
anything not confirmed for the active build as provisional.

### Berry-plot window

The companion renders the four documented plots from PNGs in the `Berry Trees`
folder beside the script. Each displayed tree uses a 16-by-32-pixel frame.
Planted stage 1 uses `BerryTreeDirtPile.png`; stage 2 alternates the two
16-by-32 halves of `SproutTree.png` every 0.5 seconds. Stages 3, 4, and 5
animate between the corresponding pair of frames in the berry's sprite sheet:
frames 1–2, 3–4, and 5–6 respectively. The berry-to-sheet assignments follow
the Sprite column above. Hover over a tree to see its berry name.

## 7. Endianness and bitfield conventions

Multibyte integer fields listed here are little-endian. Read them with an
explicit little-endian format or equivalent byte conversion; do not depend on
the host computer's native endianness.

For bitfields, bit 0 is the least significant bit of the byte. Masks should
be applied to the raw byte before interpreting flags. For example:

```python
low_nibble = value & 0x0F
high_bit = bool(value & 0x80)
```

The berry-tree status byte packs a seven-bit stage and one high-bit flag.
The watering byte packs four low-bit counter bits and four independent high
bits.

## 8. Revision and confidence notes

The offsets and layouts above describe a known Emerald Rogue 2.0.x parser
profile and EX v2.0-derived source structures; they are not a guarantee for
every release, fork, patch, or expansion. In particular:

- Sector IDs, logical block sizes, and metadata should be checked for the
  target revision.
- SaveBlock2 encryption-key and bag offsets can differ across source/build
  variants; the `0x4C` key and `0x578` bag offsets describe the companion
  parser profile, while EX v2.0-derived source references also show `0xAC`
  and `0x560`, respectively.
- The berry-tree field layout is source-derived. Validate the array offset,
  stride, and farm tree-ID map against the exact executable/build being read.
- Item IDs and berry-type conversions belong to the target revision's static
  item definitions.
- Unrecognized field values should be reported or left undecoded, not
  silently converted to plausible-looking defaults.

## 9. Validation approach for new fields

When adding another save field or supporting another revision:

1. Identify the exact game revision/build and its data definitions.
2. Reconstruct the correct logical save copy from complete, matching sectors.
3. Locate the field relative to its logical block.
4. Confirm integer widths, endianness, bit masks, and any encryption.
5. Compare the decoded field with in-game data or multiple controlled saves.
6. Record confidence and revision scope alongside the offset.
7. Keep mutable values in the save; hardcode only static game definitions.

Known data structures that are not documented here should remain marked
unknown until their offsets and encodings are independently established.
