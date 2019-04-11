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
#
#  This file is generated by build_types.py from datatype.def.
#
#  DO NOT EDIT THIS FILE DIRECTLY. Update "datatype.def" and rerun "build_types.py"
#
#  Generated on 2019-04-11 07:46

from stream.input import Input
from stream.output import Output


class JobClass(object):
    def __init__(self, stream: Input = None):
        if stream is None:
            self.base_hp = 0
            self.base_mp = 0
            self.starting_spell_level = 0
            self.base_strength = 0
            self.base_agility = 0
            self.base_intellect = 0
            self.base_stamina = 0
            self.base_luck = 0
            self.base_accuracy = 0
            self.base_evade = 0
            self.base_mdef = 0
            self.weapon_id = 0
            self.armor_id = 0
            self.unused = 0

        else:
            self.base_hp = stream.get_u16()
            self.base_mp = stream.get_u16()
            self.starting_spell_level = stream.get_u8()
            self.base_strength = stream.get_u8()
            self.base_agility = stream.get_u8()
            self.base_intellect = stream.get_u8()
            self.base_stamina = stream.get_u8()
            self.base_luck = stream.get_u8()
            self.base_accuracy = stream.get_u8()
            self.base_evade = stream.get_u8()
            self.base_mdef = stream.get_u8()
            self.weapon_id = stream.get_u8()
            self.armor_id = stream.get_u8()
            self.unused = stream.get_u8()

    def write(self, stream: Output):
        stream.put_u16(self.base_hp)
        stream.put_u16(self.base_mp)
        stream.put_u8(self.starting_spell_level)
        stream.put_u8(self.base_strength)
        stream.put_u8(self.base_agility)
        stream.put_u8(self.base_intellect)
        stream.put_u8(self.base_stamina)
        stream.put_u8(self.base_luck)
        stream.put_u8(self.base_accuracy)
        stream.put_u8(self.base_evade)
        stream.put_u8(self.base_mdef)
        stream.put_u8(self.weapon_id)
        stream.put_u8(self.armor_id)
        stream.put_u8(self.unused)


