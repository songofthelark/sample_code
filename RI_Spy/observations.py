from enum import Enum


class BaseEnum(Enum):
    def __getitem__(self, item):
        try:
            return self[item]
        except KeyError:
            return None


class Color(BaseEnum):
    R = "R"
    RO = "RO"
    OR = "OR"
    ORANGE = "O"
    Y = "Y"
    YG = "YG"
    GY = "GY"
    G = "G"
    BG = "BG"
    GB = "GB"
    B = "B"
    V = "V"
    P = "P"
    RP = "RP"
    PR = "PR"
    C = "C"
    W = "W"
    GR = "GR"
    BL = "BL"
    PI = "PI"
    BR = "BR"


class Transparency(BaseEnum):
    TP = "TP"
    STP = "STP"
    TL = "TL"
    STL = "STL"
    OPAQUE = "O"


class Phenomenon(BaseEnum):
    A = "A"
    AD = "Ad"
    AV = "Av"
    C = "C"
    CC = "CC"
    IRID = "I"
    L = "L"
    ORIENT = "O"
    P = "P"


class OpticNature(BaseEnum):
    SR = "SR"
    SRADR = "SR-ADR"
    DR = "DR"
    AGG = "AGG"


class Assembled(BaseEnum):
    Y = "Y"
    N = "N"


class StoneGroup:

    # default value is all transparencies, all colors, no phenomena, not assembled
    def __init__(self, name: str, transparency: list[Transparency] = tuple(Transparency),
                 phenomenon: list[Phenomenon] = tuple(),
                 assembled: Assembled = Assembled.N,
                 primary_colors: list[Color] = tuple(Color)):
        self.name = name
        self.transparency = transparency
        self.phenomena = phenomenon
        self.assembled = assembled
        self.primary_colors = primary_colors

    def has_primary_color(self, color: Color):
        return color in self.primary_colors

    def has_phenomenon(self, phenomenon: Phenomenon):
        return phenomenon in self.phenomena

    def is_phenomenal(self):
        return len(self.phenomena)

    def is_assembled(self):
        return Assembled.Y == self.assembled

    def has_transparency(self, transparency: Transparency):
        return transparency in self.transparency

    def __str__(self):
        return self.name


stone_groups = [

    StoneGroup("greentp", transparency=[Transparency.TP, Transparency.STP],
               primary_colors=[Color.G, Color.BG, Color.YG]),

    StoneGroup("greentl", transparency=[Transparency.TL, Transparency.STL, Transparency.OPAQUE],
               primary_colors=[Color.G, Color.BG, Color.YG]),

    StoneGroup("orangetp", transparency=[Transparency.TP, Transparency.STP],
               primary_colors=[Color.RO, Color.ORANGE, Color.Y, Color.GY, Color.BR]),

    StoneGroup("orangetl", transparency=[Transparency.TL, Transparency.STL, Transparency.OPAQUE],
               primary_colors=[Color.RO, Color.ORANGE, Color.Y, Color.GY, Color.BR]),

    StoneGroup("bluetp", transparency=[Transparency.TP, Transparency.STP],
               primary_colors=[Color.B, Color.GB, Color.V]),

    StoneGroup("bluetl", transparency=[Transparency.TL, Transparency.STL, Transparency.OPAQUE],
               primary_colors=[Color.B, Color.GB, Color.V]),

    StoneGroup("redtp", transparency=[Transparency.TP, Transparency.STP],
               primary_colors=[Color.R, Color.OR, Color.PI, Color.RP, Color.PR, Color.P]),

    StoneGroup("redtl", transparency=[Transparency.TL, Transparency.STL, Transparency.OPAQUE],
               primary_colors=[Color.R, Color.OR, Color.PI, Color.RP, Color.PR, Color.P]),

    StoneGroup("colorless", transparency=[Transparency.TP, Transparency.STP],
               primary_colors=[Color.C]),

    StoneGroup("white", transparency=[Transparency.STP, Transparency.TL, Transparency.STL, Transparency.OPAQUE],
               primary_colors=[Color.W]),

    StoneGroup("star", phenomenon=[Phenomenon.A],
               transparency=[Transparency.TL, Transparency.STL, Transparency.OPAQUE]),

    StoneGroup("catseye", phenomenon=[Phenomenon.C],
               transparency=[Transparency.TL, Transparency.STL, Transparency.OPAQUE]),

    StoneGroup("colorchange", phenomenon=[Phenomenon.CC], transparency=[Transparency.TP, Transparency.STP]),
    StoneGroup("playofcolor", phenomenon=[Phenomenon.P, Phenomenon.ORIENT, Phenomenon.IRID]),
    StoneGroup("adularescence", phenomenon=[Phenomenon.AV, Phenomenon.AD, Phenomenon.L]),
    StoneGroup("assembled", assembled=Assembled.Y),
    StoneGroup("gray", primary_colors=[Color.GR]),
    StoneGroup("black", primary_colors=[Color.BL]),

]
