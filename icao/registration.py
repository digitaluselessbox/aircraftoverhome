class Registration:
    def __init__(self):
        self.limited_alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # 24 chars; no I, O
        self.full_alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # 26 chars

        self.stride_mappings = [
            {"start": 0x008011, "s1": 26 * 26, "s2": 26, "prefix": "ZS-"},
            {"start": 0x390000, "s1": 1024, "s2": 32, "prefix": "F-G"},
            {"start": 0x398000, "s1": 1024, "s2": 32, "prefix": "F-H"},
            {"start": 0x3c4421, "s1": 1024, "s2": 32, "prefix": "D-A", "first": "AAA", "last": "OZZ"},
            {"start": 0x3c0001, "s1": 26 * 26, "s2": 26, "prefix": "D-A", "first": "PAA", "last": "ZZZ"},
            {"start": 0x3c8421, "s1": 1024, "s2": 32, "prefix": "D-B", "first": "AAA", "last": "OZZ"},
            {"start": 0x3c2001, "s1": 26 * 26, "s2": 26, "prefix": "D-B", "first": "PAA", "last": "ZZZ"},
            {"start": 0x3cc000, "s1": 26 * 26, "s2": 26, "prefix": "D-C"},
            {"start": 0x3d04a8, "s1": 26 * 26, "s2": 26, "prefix": "D-E"},
            {"start": 0x3d4950, "s1": 26 * 26, "s2": 26, "prefix": "D-F"},
            {"start": 0x3d8df8, "s1": 26 * 26, "s2": 26, "prefix": "D-G"},
            {"start": 0x3dd2a0, "s1": 26 * 26, "s2": 26, "prefix": "D-H"},
            {"start": 0x3e1748, "s1": 26 * 26, "s2": 26, "prefix": "D-I"},
            {"start": 0x448421, "s1": 1024, "s2": 32, "prefix": "OO-"},
            {"start": 0x458421, "s1": 1024, "s2": 32, "prefix": "OY-"},
            {"start": 0x460000, "s1": 26 * 26, "s2": 26, "prefix": "OH-"},
            {"start": 0x468421, "s1": 1024, "s2": 32, "prefix": "SX-"},
            {"start": 0x490421, "s1": 1024, "s2": 32, "prefix": "CS-"},
            {"start": 0x4a0421, "s1": 1024, "s2": 32, "prefix": "YR-"},
            {"start": 0x4b8421, "s1": 1024, "s2": 32, "prefix": "TC-"},
            {"start": 0x740421, "s1": 1024, "s2": 32, "prefix": "JY-"},
            {"start": 0x760421, "s1": 1024, "s2": 32, "prefix": "AP-"},
            {"start": 0x768421, "s1": 1024, "s2": 32, "prefix": "9V-"},
            {"start": 0x778421, "s1": 1024, "s2": 32, "prefix": "YK-"},
            {"start": 0x7c0000, "s1": 36 * 36, "s2": 36, "prefix": "VH-"},
            {"start": 0xc00001, "s1": 26 * 26, "s2": 26, "prefix": "C-F"},
            {"start": 0xc044a9, "s1": 26 * 26, "s2": 26, "prefix": "C-G"},
            {"start": 0xe01041, "s1": 4096, "s2": 64, "prefix": "LV-"},
        ]

        self.numeric_mappings = [
            {"start": 0x140000, "first": 0, "count": 100000, "template": "RA-00000"},
            {"start": 0x0b03e8, "first": 1000, "count": 1000, "template": "CU-T0000"},
        ]

        for mapping in self.stride_mappings:
            if "alphabet" not in mapping:
                mapping["alphabet"] = self.full_alphabet

            if "first" in mapping:
                c1 = mapping["alphabet"].index(mapping["first"][0])
                c2 = mapping["alphabet"].index(mapping["first"][1])
                c3 = mapping["alphabet"].index(mapping["first"][2])
                mapping["offset"] = c1 * mapping["s1"] + c2 * mapping["s2"] + c3
            else:
                mapping["offset"] = 0

            if "last" in mapping:
                c1 = mapping["alphabet"].index(mapping["last"][0])
                c2 = mapping["alphabet"].index(mapping["last"][1])
                c3 = mapping["alphabet"].index(mapping["last"][2])
                mapping["end"] = mapping["start"] - mapping["offset"] + c1 * mapping["s1"] + c2 * mapping["s2"] + c3
            else:
                mapping["end"] = mapping["start"] - mapping["offset"] + (len(mapping["alphabet"]) - 1) * mapping["s1"] + (len(mapping["alphabet"]) - 1) * mapping["s2"] + (len(mapping["alphabet"]) - 1)

        for mapping in self.numeric_mappings:
            mapping["end"] = mapping["start"] + mapping["count"] - 1

    def lookup(self, hex_id):
        reg = self.database_reg(hex_id)
        if reg:
            return reg

        hex_id = int(hex_id, 16)
        if hex_id is None:
            return None

        reg = self.n_reg(hex_id)
        if reg:
            return reg

        reg = self.ja_reg(hex_id)
        if reg:
            return reg

        reg = self.hl_reg(hex_id)
        if reg:
            return reg

        reg = self.numeric_reg(hex_id)
        if reg:
            return reg

        reg = self.stride_reg(hex_id)
        if reg:
            return reg

        return None

    def database_reg(self, hex_id):
        return window.fr24db.get(hex_id, "")

    def stride_reg(self, hex_id):
        for mapping in self.stride_mappings:
            if hex_id < mapping["start"] or hex_id > mapping["end"]:
                continue

            offset = hex_id - mapping["start"] + mapping["offset"]
            i1 = offset // mapping["s1"]
            offset %= mapping["s1"]
            i2 = offset // mapping["s2"]
            offset %= mapping["s2"]
            i3 = offset

            if i1 < 0 or i1 >= len(mapping["alphabet"]) or i2 < 0 or i2 >= len(mapping["alphabet"]) or i3 < 0 or i3 >= len(mapping["alphabet"]):
                continue

            return mapping["prefix"] + mapping["alphabet"][i1] + mapping["alphabet"][i2] + mapping["alphabet"][i3]

        return None

    def numeric_reg(self, hex_id):
        for mapping in self.numeric_mappings:
            if hex_id < mapping["start"] or hex_id > mapping["end"]:
                continue

            reg = str(hex_id - mapping["start"] + mapping["first"])
            return mapping["template"][:len(mapping["template"]) - len(reg)] + reg

    def n_letters(self, rem):
        if rem == 0:
            return ""

        rem -= 1
        return self.limited_alphabet[rem // 25] + self.n_letter(rem % 25)

    def n_letter(self, rem):
        if rem == 0:
            return ""

        rem -= 1
        return self.limited_alphabet[rem]

    def n_reg(self, hex_id):
        offset = hex_id - 0xa00001
        if offset < 0 or offset >= 915399:
            return None

        digit1 = offset // 101711 + 1
        reg = "N" + str(digit1)
        offset %= 101711
        if offset <= 600:
            return reg + self.n_letters(offset)

        offset -= 601
        digit2 = offset // 10111
        reg += str(digit2)
        offset %= 10111

        if offset <= 600:
            return reg + self.n_letters(offset)

        offset -= 601
        digit3 = offset // 951
        reg += str(digit3)
        offset %= 951

        if offset <= 600:
            return reg + self.n_letters(offset)

        offset -= 601
        digit4 = offset // 35
        reg += str(digit4)
        offset %= 35

        if offset <= 24:
            return reg + self.n_letter(offset)

        offset -= 25
        return reg + str(offset)

    def hl_reg(self, hex_id):
        if 0x71ba00 <= hex_id <= 0x71bf99:
            return "HL" + hex(hex_id - 0x71ba00 + 0x7200)[2:]

        if 0x71c000 <= hex_id <= 0x71c099:
            return "HL" + hex(hex_id - 0x71c000 + 0x8000)[2:]

        if 0x71c200 <= hex_id <= 0x71c299:
            return "HL" + hex(hex_id - 0x71c200 + 0x8200)[2:]

        return None

    def ja_reg(self, hex_id):
        offset = hex_id - 0x840000
        if offset < 0 or offset >= 229840:
            return None

        reg = "JA"
        digit1 = offset // 22984
        if digit1 < 0 or digit1 > 9:
            return None
        reg += str(digit1)
        offset %= 22984

        digit2 = offset // 916
        if digit2 < 0 or digit2 > 9:
            return None
        reg += str(digit2)
        offset %= 916

        if offset < 340:
            digit3 = offset // 34
            reg += str(digit3)
            offset %= 34

            if offset < 10:
                return reg + str(offset)

            offset -= 10
            return reg + self.limited_alphabet[offset]

        offset -= 340
        letter3 = offset // 24
        return reg + self.limited_alphabet[letter3] + self.limited_alphabet[offset % 24]