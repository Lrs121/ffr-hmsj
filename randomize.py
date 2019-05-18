#!/usr/bin/env python3

#  Copyright 2019 Nicole Borrelli
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import os
import random
from argparse import ArgumentParser
from random import seed, randint

from doslib.event import EventTextBlock, EventTable
from doslib.gen.classes import JobClass
from doslib.gen.enemy import EnemyStats
from doslib.rom import Rom
from doslib.textblock import TextBlock
from event import easm
from ipsfile import load_ips_files
from randomizer.flags import Flags
from randomizer.keyitemsolver import KeyItemPlacement
from randomizer.spellshuffle import SpellShuffle
from randomizer.treasures import treasure_shuffle
from stream.outputstream import OutputStream

BASE_PATCHES = [
    "data/DataPointerConsolidation.ips",
    "data/ImprovedEquipmentStatViewing.ips",
    "data/NoEscape.ips",
    "data/RunningChange.ips",
    "data/StatusScreenExpansion.ips",
    "data/SpellLevelFix.ips",
    "data/SpriteFrameLoaderFix.ips"
]


def randomize_rom(rom: Rom, flags: Flags, rom_seed: str) -> Rom:
    patches_to_load = BASE_PATCHES
    if flags.encounters is not None:
        patches_to_load.append("data/FF1EncounterToggle.ips")
    if flags.default_party is not None:
        patches_to_load.append("data/RandomDefault.ips")

    base_patch = load_ips_files(*patches_to_load)
    rom = rom.apply_patches(base_patch)

    rom = init_base_events(rom)

    event_text_block = EventTextBlock(rom)
    event_text_block.shrink()
    rom = event_text_block.pack(rom)

    rom = update_xp_requirements(rom, flags.exp_mult)

    if flags.key_item_shuffle is not None:
        placement = KeyItemPlacement(rom, random.randint(0, 0xffffffff))
        rom = placement.rom

    if flags.magic is not None:
        shuffle_magic = SpellShuffle(rom)
        rom = shuffle_magic.write(rom)

    if flags.treasures is not None:
        rom = treasure_shuffle(rom)

    if flags.debug is not None:
        class_stats_stream = rom.open_bytestream(0x1E1354, 96)
        class_stats = []
        while not class_stats_stream.is_eos():
            class_stats.append(JobClass(class_stats_stream))

        class_out_stream = OutputStream()
        for job_class in class_stats:
            # Set the starting weapon and armor for all classes to something
            # very fair and balanced: Masamune + Diamond Armlet. :)
            job_class.weapon_id = 0x28
            job_class.armor_id = 0x0e

            # Write the (very balanced) new data out
            job_class.write(class_out_stream)

        rom = rom.apply_patch(0x1E1354, class_out_stream.get_buffer())

    if True:
        enemy_data_stream = rom.open_bytestream(0x1DE044, 0x1860)
        enemies = []
        while not enemy_data_stream.is_eos():
            enemies.append(EnemyStats(enemy_data_stream))

        # Rebalance (Revisited) Fiend HP
        enemies[0x78].max_hp = enemies[0x77].max_hp * 2
        enemies[0x7a].max_hp = enemies[0x79].max_hp * 2
        enemies[0x7c].max_hp = enemies[0x7b].max_hp * 2
        enemies[0x7e].max_hp = enemies[0x7d].max_hp * 2

        # And Chaos
        enemies[0x7f].max_hp = enemies[0x7e].max_hp * 2

        # Finally, Piscodemons can suck it
        enemies[0x67].atk = int(enemies[0x67].atk / 2)

        # We'll also lower everyone's INT just to see how that works
        for index in range(0x80):
            enemies[index].intel = int(.666 * enemies[index].intel)
            # print(f"{hex(index)} HP: {enemies[index].max_hp}, INT: {enemies[index].intel}")

        out = OutputStream()
        for enemy in enemies:
            enemy.write(out)
        rom = rom.apply_patch(0x1DE044, out.get_buffer())

    # Add the seed + flags to the party creation screen.
    seed_str = TextBlock.encode_text(f"Seed:\n{rom_seed}\nFlags:\n{flags}\x00")
    pointer = OutputStream()
    pointer.put_u32(0x8227054)
    rom = rom.apply_patches({
        0x227054: seed_str,
        0x4d8d4: pointer.get_buffer()
    })

    return rom


def gen_seed(rom_seed: str) -> str:
    """Reduces a seed to the first 10 chars.

    Pulling this out for future caching, should we desire.
    :param rom_seed: Raw input seed
    :return: String of the seed
    """
    if rom_seed is None:
        rom_seed = hex(randint(0, 0xffffffff))
    elif len(rom_seed) > 10:
        rom_seed = rom_seed[0:10]

    out_seed = rom_seed
    seed(rom_seed)
    return str(out_seed)


def get_filename(base_path: str, flags: Flags, seed: str) -> str:
    filename = base_path
    if filename.find(os.sep) > -1:
        filename = filename[0:filename.rfind(os.sep)]
    if filename.endswith(".gba"):
        filename = filename[:len(filename) - 4]
    return f"{filename}_{flags.text()}_{seed}.gba"


def randomize(rom_path: str, flags: Flags, rom_seed: str):
    rom_seed = gen_seed(rom_seed)
    rom = Rom(rom_path)
    rom = randomize_rom(rom, flags, rom_seed)

    rom.write(get_filename(rom_path, flags, rom_seed))


def update_xp_requirements(rom: Rom, value) -> Rom:
    level_data = rom.open_bytestream(0x1BE3B4, 396)
    new_table = OutputStream()
    next_value = level_data.get_u32()
    while next_value is not None:
        new_table.put_u32(int(next_value * value))
        next_value = level_data.get_u32()
    rom = rom.apply_patch(0x1BE3B4, new_table.get_buffer())
    return rom


def init_base_events(rom: Rom) -> Rom:
    """This method sets up the core changes required for the randomizer.

    This method specifically sets up the following:

    - Shows the airship from the start.
    - Changes the flag for the desert cut-scene from 0x15 (having the airship) to 0x28
      which used to be set by listening to the King's plight in Cornelia Castle.
    - Removes the guards from Cornelia who send you to the King.
    - Removes the locked door in Chaos Shrine that would normally prevent you from accessing Garland
      before talking to the King.
    - Remove setting a pose on Princess Sara, since she may be shuffled.
    - Move the airship to right in front of Castle Cornelia.

    :param rom:
    :return:
    """
    map_init_events = EventTable(rom, 0x7050, 0xD3)
    world_map_id = 0x0
    chaos_shrine_map_id = 0x1f
    crescent_lake_map_id = 0x2f
    cornelia_map_id = 0x3a

    world_map_init = """
        %airship_visible 0x15
        %have_chime 0x1f
        %item_from_desert 0x28

        set_flag 0x9
        set_flag %airship_visible
        check_flag %item_from_desert jz .Label_2
        remove_trigger 0x138e
        .Label_2:
        check_flag %have_chime jnz .Label_3
        db 0x2f 0x8 0x0 0x0 0xff 0xb8 0x38 0x2
        .Label_3:
        npc_update 0x4 0x0
        npc_update 0x4 0x1
        npc_update 0x4 0x2
        npc_update 0x4 0x3
        npc_update 0x4 0x4
        npc_update 0x4 0x5
        end_event
    """
    world_map_event_addr = map_init_events.get_addr(world_map_id)
    world_map_event = easm.parse(world_map_init, world_map_event_addr)

    cornelia_map_init = """
        remove_all 0x138c
        end_event
    """
    cornelia_map_event_addr = map_init_events.get_addr(cornelia_map_id)
    cornelia_map_event = easm.parse(cornelia_map_init, cornelia_map_event_addr)

    chaos_shrine_init = """
        check_flag 0x1 jz .Label_3
        remove_trigger 0x138b
        remove_trigger 0x138b
        check_flag 0x9 jz .Label_2
        remove_trigger 0x1f4a
        remove_trigger 0x1f4a
        jump .Label_2
        .Label_3:
        db 0x2f 0x8 0x0 0x0 0xff 0x25 0x1c 0x8
        db 0x2f 0x8 0x0 0x0 0xff 0x25 0x1d 0x8
        db 0x2f 0x8 0x0 0x0 0xff 0x27 0x1c 0x8
        db 0x2f 0x8 0x0 0x0 0xff 0x27 0x1d 0x8
        .Label_2:
        check_flag 0x24 jz .Label_4
        remove_trigger 0x1f4c
        jump .Label_5
        .Label_4:
        check_flag 0x13 jz .Label_5
        check_flag 0x1d jz .Label_5
        check_flag 0x22 jz .Label_5
        npc_update 0x1 0x7
        db 0x2f 0x8 0x0 0x0 0xff 0x25 0x1c 0x8
        db 0x2f 0x8 0x0 0x0 0xff 0x27 0x1c 0x8
        db 0x2f 0x8 0x0 0x0 0xff 0x26 0x1d 0x8
        .Label_5:
        end_event
    """
    chaos_shrine_event_addr = map_init_events.get_addr(chaos_shrine_map_id)
    chaos_shrine_map_event = easm.parse(chaos_shrine_init, chaos_shrine_event_addr)

    crescent_lake_map_init = """
        %earth_crystal_lit 0x11
        %lukahn_npc_id 0xd
        %have_canoe 0x12

        %give_canoe_event 0x1394
        
        check_flag %have_canoe jnz .End_of_Event
        check_flag %earth_crystal_lit jz .End_of_Event
        set_npc_event %lukahn_npc_id %give_canoe_event
        .End_of_Event:
        end_event
    """
    crescent_lake_map_event_addr = map_init_events.get_addr(crescent_lake_map_id)
    crescent_lake_map_event = easm.parse(crescent_lake_map_init, crescent_lake_map_event_addr)

    # Move the airship's start location to right outside of Coneria Castle.
    airship_start = OutputStream()
    airship_start.put_u32(0x918)
    airship_start.put_u32(0x998)

    return rom.apply_patches({
        0x65280: airship_start.get_buffer(),
        Rom.pointer_to_offset(world_map_event_addr): world_map_event,
        Rom.pointer_to_offset(cornelia_map_event_addr): cornelia_map_event,
        Rom.pointer_to_offset(chaos_shrine_event_addr): chaos_shrine_map_event,
        Rom.pointer_to_offset(crescent_lake_map_event_addr): crescent_lake_map_event,
    })


def shuffle_key_items(rom: Rom) -> Rom:
    # The Key items returned work like this. Suppose a Placement returned was
    # `Placement(item='oxyale', location='king')` this means that the "Oxyale" key item
    # should be found in the King of Cornelia location.
    #
    # This does *NOT* mean the King of Cornelia will give you Oxyale, rather, it means the NPC
    # that gives Oxyale (the Fairy) should be placed in the King's spot.
    #
    # Further, the Fairy in the King of Cornelia's spot, will be there at the start of the game, and
    # won't need to be rescued from the Bottle. It *does* mean that the Fairy won't provide Oxyale
    # until Garland is defeated and that NPC (or treasure) is itself rescued.

    key_item_locations = KeyItemPlacement(rom, randint(0, 0xffffffff))
    key_item_locations.maps.write(rom)
    return rom


def main() -> int:
    parser = ArgumentParser(description="Final Fantasy Dawn of Souls Randomizer")
    parser.add_argument("rom", metavar="ROM file", type=str, help="The ROM file to randomize.")
    parser.add_argument("--seed", dest="seed", nargs=1, type=str, action="append", help="Seed value to use")
    parser.add_argument("--flags", dest="flags", nargs=1, type=str, action="append", required=True, help="Flags")
    parsed = parser.parse_args()

    # Ensure there's at most 1 seed.
    if parsed.seed is not None:
        seed_list = parsed.seed[0]
        if len(seed_list) > 1:
            parser.error("pass at most 1 value with --seed")
            return -1
        seed_value = seed_list[0]
    else:
        seed_value = None

    # It's possible to pass multiple --flags parameters, so collect them together and parse them.
    collected_flags = ""
    for flags in parsed.flags:
        collected_flags += f" {flags[0]}"
    flags = Flags(collected_flags)

    randomize(parsed.rom, flags, seed_value)
    return 0


if __name__ == "__main__":
    main()
