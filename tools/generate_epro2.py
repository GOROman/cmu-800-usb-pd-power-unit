#!/usr/bin/env python3
"""Generate the CMU-800 USB-PD replacement PSU schematic.

The output is an EasyEDA Pro v3 ``.epru`` source file and a packaged
``.epro2`` project.  The project deliberately contains a schematic only:
the original CMU-800 enclosure/board measurements are not yet known, so a
fabrication PCB is not generated from guessed dimensions.

The epru records are intentionally deterministic.  This makes the source
reviewable in git and lets verify_epro2.py check the generated project without
requiring a running EasyEDA bridge.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "easyeda"
PROJECT = "CMU800_USB_PD_Power_Unit"
UPDATE_TIME = 1788123456000


def uid(label: str) -> str:
    """Return a stable EasyEDA-style 16-hex-character identifier."""

    return hashlib.sha256(label.encode("utf-8")).hexdigest()[:16]


def compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class Pin:
    number: str
    name: str
    x: float
    y: float
    rotation: int
    pin_type: str = "Undefined"


@dataclass(frozen=True)
class Part:
    name: str
    lcsc: str
    prefix: str
    value: str
    footprint: str
    pins: tuple[Pin, ...]
    bbox: tuple[float, float, float, float]
    title: str | None = None

    @property
    def part_id(self) -> str:
        return f"{self.name}.1"

    @property
    def symbol_uuid(self) -> str:
        return uid(f"symbol:{self.part_id}")

    @property
    def footprint_uuid(self) -> str:
        return uid(f"footprint:{self.part_id}")

    @property
    def device_uuid(self) -> str:
        return uid(f"device:{self.part_id}")


def p(number: str, name: str, x: float, y: float, rotation: int,
      pin_type: str = "Undefined") -> Pin:
    return Pin(number, name, x, y, rotation, pin_type)


def make_parts() -> list[Part]:
    """Return schematic symbols used by the replacement PSU."""

    def resistor(name: str, code: str, value: str, footprint: str = "R_0603") -> Part:
        return Part(name, code, "R", value, footprint,
                    (p("1", "1", -30, 0, 0), p("2", "2", 30, 0, 180)),
                    (-20, -10, 20, 10))

    def capacitor(name: str, code: str, value: str, footprint: str = "C_0603") -> Part:
        return Part(name, code, "C", value, footprint,
                    (p("1", "+", 0, -30, 270), p("2", "-", 0, 30, 90)),
                    (-15, -20, 15, 20))

    def diode(name: str, code: str, value: str, footprint: str = "D_1206") -> Part:
        return Part(name, code, "D", value, footprint,
                    (p("1", "K", -30, 0, 0), p("2", "A", 30, 0, 180)),
                    (-18, -10, 18, 10))

    parts: list[Part] = []

    # USB-C receptacle.  The two VBUS and two GND groups are deliberately
    # represented as separate pins even though each group shares one net.
    parts.append(Part(
        "TYPE-C16PIN_C393939", "C393939", "J", "USB-C receptacle, sink",
        "USB_C_16P_SMD", (
            p("A1B12", "GND", -65, -75, 0, "Power"),
            p("A4B9", "VBUS", -65, -65, 0, "Power"),
            p("A5", "CC1", -65, -55, 0),
            p("A6", "DP1", -65, -45, 0),
            p("A7", "DN1", -65, -35, 0),
            p("A8", "SBU1", -65, -25, 0),
            p("B5", "CC2", -65, -15, 0),
            p("B6", "DP2", -65, -5, 0),
            p("B7", "DN2", -65, 5, 0),
            p("B8", "SBU2", -65, 15, 0),
            p("B4A9", "VBUS", -65, 25, 0, "Power"),
            p("B1A12", "GND", -65, 35, 0, "Power"),
            p("S1", "SHIELD", -65, 55, 0),
            p("S2", "SHIELD", -65, 65, 0),
            p("S3", "SHIELD", -65, 75, 0),
            p("S4", "SHIELD", -65, 85, 0),
        ), (-50, -95, 50, 95), "USB-C sink input"))

    parts.append(Part(
        "STUSB4500QTR_C2678061", "C2678061", "U", "STUSB4500QTR",
        "QFN-24-EP_4x4", (
            p("1", "CC1DB", -80, -55, 0), p("2", "CC1", -80, -45, 0),
            p("3", "NC", -80, -35, 0), p("4", "CC2", -80, -25, 0),
            p("5", "CC2DB", -80, -15, 0), p("6", "RESET", -80, -5, 0),
            p("7", "SCL", -80, 5, 0), p("8", "SDA", -80, 15, 0),
            p("9", "DISCH", -80, 25, 0), p("10", "GND", -80, 35, 0, "Power"),
            p("11", "ATTACH", -80, 45, 0), p("12", "ADDR0", -80, 55, 0),
            p("13", "ADDR1", 80, 55, 180), p("14", "POWER_OK3", 80, 45, 180),
            p("15", "GPIO", 80, 35, 180), p("16", "VBUS_EN_SNK", 80, 25, 180),
            p("17", "A_B_SIDE", 80, 15, 180), p("18", "VBUS_VS_DISCH", 80, 5, 180),
            p("19", "ALERT", 80, -5, 180), p("20", "POWER_OK2", 80, -15, 180),
            p("21", "VREG_1V2", 80, -25, 180, "Power"),
            p("22", "VSYS", 80, -35, 180, "Power"),
            p("23", "VREG_2V7", 80, -45, 180, "Power"),
            p("24", "VDD", 80, -55, 180, "Power"),
            p("25", "EP", 0, -75, 90, "Power"),
        ), (-70, -65, 70, 65), "USB-PD sink controller"))

    parts.append(Part(
        "AO3401A_C15127", "C15127", "Q", "AO3401A P-channel MOSFET",
        "SOT-23", (p("1", "S", -35, -15, 0, "Power"),
                   p("3", "G", -35, 15, 0), p("2", "D", 35, 0, 180, "Power")),
        (-25, -25, 25, 25)))

    parts.append(Part(
        "WRB2405S-3WR2_C5369677", "C5369677", "U", "WRB2405S-3WR2, isolated 5 V",
        "SIP-7_22x9.5", (
            p("1", "-VIN", -50, -20, 0, "Power"), p("2", "+VIN", -50, -10, 0, "Power"),
            p("3", "CTRL", -50, 10, 0), p("5", "NC", -50, 20, 0),
            p("6", "+VO", 50, -10, 180, "Power"), p("7", "-VO", 50, 10, 180, "Power"),
            p("8", "CS", 50, 20, 180)), (-40, -35, 40, 35), "isolated 5 V DC/DC"))

    parts.append(Part(
        "WRA2415S-3WR2_C5369663", "C5369663", "U", "WRA2415S-3WR2, isolated +/-15 V",
        "SIP-7_22x9.5", (
            p("1", "-VIN", -50, -30, 0, "Power"), p("2", "+VIN", -50, -20, 0, "Power"),
            p("3", "CTRL", -50, -10, 0), p("5", "NC", -50, 0, 0),
            p("6", "+VOUT", 50, 10, 180, "Power"), p("7", "COM", 50, 20, 180, "Power"),
            p("8", "-VOUT", 50, 30, 180, "Power")), (-40, -45, 40, 45), "isolated +/-15 V DC/DC"))

    parts.append(Part(
        "HDR5_CMU800", "TBD", "J", "CN1/CN3 compatible 5-pin output",
        "HDR-1x05_2.54mm", tuple(
            p(str(n), name, -45, -40 + (n - 1) * 20, 0, "Power")
            for n, name in ((1, "A_GND"), (2, "-15V"), (3, "+15V"), (4, "D_GND"), (5, "+5V"))
        ), (-30, -55, 30, 55)))
    parts.append(Part(
        "HDR5_STUSB_PROG", "TBD", "J", "STUSB4500 I2C/NVM programming header",
        "HDR-1x05_2.54mm", (
            p("1", "VDD", -45, -40, 0, "Power"),
            p("2", "PD_GND", -45, -20, 0, "Power"),
            p("3", "SCL", -45, 0, 0), p("4", "SDA", -45, 20, 0),
            p("5", "RESET", -45, 40, 0),
        ), (-30, -55, 30, 55), "STUSB4500 programming/test header"))

    parts.extend([
        Part("PTC_1206L110_30V_C49318383", "C49318383", "F", "1206L110 30 V resettable fuse",
             "1206", (p("1", "IN", -30, 0, 0, "Power"), p("2", "OUT", 30, 0, 180, "Power")), (-18, -8, 18, 8)),
        diode("SMBJ24A_TVS_C41425647", "C41425647", "SMBJ24A surge clamp", "SMBJ"),
        diode("ESDA25W_CC1_C1974707", "C1974707", "ESDA25W CC protection", "SOD-323"),
        diode("ESDA25W_CC2_C1974707", "C1974707", "ESDA25W CC protection", "SOD-323"),
        resistor("R_100K_C25803", "C25803", "100 kOhm", "R_0603"),
        resistor("R_100_C22775", "C22775", "100 Ohm", "R_0603"),
        resistor("R_1K_TBD", "TBD", "1 kOhm", "R_0603"),
        resistor("R_100K_RESET_C25803", "C25803", "100 kOhm reset pulldown", "R_0603"),
        resistor("R_4K7_C23162", "C23162", "4.7 kOhm I2C pull-up", "R_0603"),
        resistor("R_160R_0V5_TBD", "TBD", "160 Ohm, >=0.5 W", "R_1210"),
        resistor("R_3K_0V5_A_PLUS_TBD", "TBD", "3.0 kOhm, >=0.5 W", "R_1210"),
        resistor("R_3K_0V5_A_MINUS_TBD", "TBD", "3.0 kOhm, >=0.5 W", "R_1210"),
        capacitor("C_4U7_50V_C5246584", "C5246584", "4.7 uF 50 V", "C_D4_L5.4"),
        capacitor("C_100N_50V_C38141", "C38141", "100 nF 50 V", "C_0805"),
        capacitor("C_10U_50V_MODULE_TBD", "TBD", "10 uF 50 V, DC/DC input", "C_1206"),
        capacitor("C_1U0_50V_MODULE_TBD", "TBD", "1.0 uF 50 V, DC/DC input", "C_0805"),
        capacitor("C_1U0_VREG_TBD", "TBD", "1.0 uF, VREG decoupling", "C_0603"),
        capacitor("C_100U_25V_TBD_1", "C4747965", "100 uF 25 V", "C_D6.3"),
        capacitor("C_100U_25V_TBD_2", "C4747965", "100 uF 25 V", "C_D6.3"),
        capacitor("C_100U_25V_TBD_3", "C4747965", "100 uF 25 V", "C_D6.3"),
        capacitor("C_100U_25V_TBD_4", "C4747965", "100 uF 25 V", "C_D6.3"),
        capacitor("C_100N_50V_TBD_1", "C38141", "100 nF 50 V", "C_0805"),
        capacitor("C_100N_50V_TBD_2", "C38141", "100 nF 50 V", "C_0805"),
        capacitor("C_100N_50V_TBD_3", "C38141", "100 nF 50 V", "C_0805"),
        capacitor("C_100N_50V_TBD_4", "C38141", "100 nF 50 V", "C_0805"),
    ])
    return parts


class Epru:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.ticket = 1

    def record(self, typ: str, body: object, rec_id: str | None = None) -> None:
        header: dict[str, object] = {"type": typ, "ticket": self.ticket}
        if rec_id is not None:
            header["id"] = rec_id
        self.ticket += 1
        self.lines.append(f"{compact(header)}||{compact(body)}|")

    def dochead(self, doc_type: str, section_uuid: str) -> None:
        self.record("DOCHEAD", {
            "docType": doc_type,
            "client": uid(f"client:{doc_type}:{section_uuid}"),
            "uuid": section_uuid,
            "updateTime": UPDATE_TIME,
            "version": str(UPDATE_TIME),
        })

    @staticmethod
    def attr_body(part_id: str, parent_id: str, key: str, value: object,
                  z_index: int, *, value_visible: bool = False,
                  key_visible: bool = False, x: object = None,
                  y: object = None, rotation: object = 0) -> dict:
        return {
            "partId": part_id, "groupId": "", "locked": False,
            "zIndex": z_index, "parentId": parent_id, "key": key,
            "value": value, "keyVisible": key_visible,
            "valueVisible": value_visible, "x": x, "y": y,
            "rotation": rotation, "color": None, "fillColor": None,
            "fontFamily": None, "fontSize": None, "fontWeight": None,
            "italic": None, "underline": None, "align": None,
        }

    def add_symbol(self, part: Part) -> None:
        self.dochead("SYMBOL", part.symbol_uuid)
        self.record("CANVAS", {"originX": 0, "originY": 0}, "CANVAS")
        self.record("PART", {"BBOX": list(part.bbox),
                              "title": f"{part.part_id}"}, part.part_id)
        self.record("ATTR", self.attr_body(part.part_id, "", "Symbol",
                                             part.title or part.name, 1), "sym-symbol")
        self.record("ATTR", self.attr_body(part.part_id, "", "Designator",
                                             f"{part.prefix}?", 2), "sym-designator")
        # A simple body is enough for a library symbol and keeps the generated
        # file easy to inspect.  Pin locations/numbers are the authoritative
        # information used by the static netlist checker.
        x1, y1, x2, y2 = part.bbox
        self.record("RECT", {
            "partId": part.part_id, "groupId": "", "locked": False,
            "zIndex": 3, "dotX1": x1 + 10, "dotY1": y2 - 10,
            "dotX2": x2 - 10, "dotY2": y1 + 10, "radiusX": 2,
            "radiusY": 2, "rotation": 0, "strokeColor": None,
            "strokeStyle": None, "fillColor": None, "strokeWidth": None,
            "fillStyle": None,
        }, "sym-body")
        for index, pin in enumerate(part.pins, start=1):
            pin_id = f"pin-{index}"
            self.record("PIN", {
                "partId": part.part_id, "groupId": "", "locked": False,
                "zIndex": 3 + index, "display": True, "x": pin.x,
                "y": pin.y, "length": 10, "rotation": pin.rotation,
                "color": None, "pinShape": "NONE",
            }, pin_id)
            for offset, (key, value) in enumerate((
                ("Pin Name", pin.name), ("Pin Number", pin.number),
                ("Pin Type", pin.pin_type)), start=1):
                self.record("ATTR", self.attr_body(
                    part.part_id, pin_id, key, value, 10 * index + offset,
                    value_visible=(key != "Pin Type")),
                    f"{pin_id}-{key.replace(' ', '-').lower()}")
        self.record("META", {"title": part.title or part.name,
                              "description": "",
                              "tags": ["CMU-800 PSU"],
                              "docType": 2, "source": ""}, "sym-meta")

    def add_footprint(self, part: Part) -> None:
        self.dochead("FOOTPRINT", part.footprint_uuid)
        layers = [
            ("TOP", "Top Layer"), ("BOTTOM", "Bottom Layer"),
            ("TOP_SILK", "Top Silkscreen Layer"),
            ("TOP_SOLDER_MASK", "Top Solder Mask Layer"),
            ("OUTLINE", "Board Outline Layer"),
        ]
        for layer_type, layer_name in layers:
            self.record("LAYER", {
                "layerType": layer_type, "layerName": layer_name,
                "use": True, "show": True, "locked": False,
                "activeColor": "#FF0000", "activateTransparency": 1,
                "inactiveColor": "#7F0000", "inactiveTransparency": 1,
            })
        self.record("ACTIVE_LAYER", {"layerId": 1})
        self.record("CANVAS", {
            "originX": 0, "originY": 0, "unit": "mm", "gridXSize": 10,
            "gridYSize": 10, "snapXSize": 0.5, "snapYSize": 0.5,
            "gridType": "NONE", "multiGridType": "NONE",
            "highlightValue": 0.5,
        }, "CANVAS")
        self.record("ELE_PLACEHOLDER", {"dataType": "PAD", "max": len(part.pins)},
                    "fp-pads")
        # This footprint is a schematic attachment placeholder rather than a
        # fabrication-ready package.  It is intentionally not used to make a
        # PCB until the mechanical dimensions have been measured.
        for index, pin in enumerate(part.pins, start=1):
            if len(part.pins) == 1:
                cx, cy = 0, 0
            else:
                cx = -50 if index <= (len(part.pins) + 1) // 2 else 50
                side_index = index - 1 if cx < 0 else index - ((len(part.pins) + 1) // 2) - 1
                cy = (side_index - 1) * 37.4
            self.record("PAD", {
                "groupId": 0, "netName": "", "layerId": 1,
                "num": part.pins[index - 1].number, "centerX": float(cx),
                "centerY": float(cy), "padAngle": 0, "hole": None,
                "defaultPad": {
                    "padWidth": 15.748, "padHeight": 37.402,
                    "shape": "RECT", "rotation": 0,
                    "offset": {"dx": 0, "dy": 0}, "expand": 0,
                }, "locked": False, "zIndex": index, "polyType": "VIA",
            }, f"pad-{index}")
        self.record("ATTR", {
            "groupId": 0, "parentId": "", "layerId": 3,
            "x": None, "y": None, "key": "Footprint",
            "value": part.footprint, "keyVisible": False,
            "valueVisible": True, "rotation": 0, "color": None,
            "fillColor": None, "fontFamily": None, "fontSize": None,
            "fontWeight": None, "italic": None, "underline": None,
            "align": None,
        }, "fp-name")
        self.record("ATTR", {
            "groupId": 0, "parentId": "", "layerId": 3,
            "x": None, "y": None, "key": "Designator",
            "value": f"{part.prefix}?", "keyVisible": False,
            "valueVisible": True, "rotation": 0, "color": None,
            "fillColor": None, "fontFamily": None, "fontSize": None,
            "fontWeight": None, "italic": None, "underline": None,
            "align": None,
        }, "fp-designator")
        self.record("NET", {"netType": None, "specialColor": None,
                              "retLine": True, "differentialName": None,
                              "isPositiveNet": False,
                              "equalLengthGroupName": None})
        self.record("META", {"title": part.footprint, "description": "",
                              "tags": [], "docType": 4, "source": ""}, "fp-meta")

    def add_device(self, part: Part) -> None:
        self.dochead("DEVICE", part.device_uuid)
        self.record("META", {
            "title": part.title or part.name,
            "tags": ["CMU-800 PSU"], "source": "", "images": [""],
            "attributes": {
                "Supplier Part": part.lcsc,
                "Manufacturer": "see BOM",
                "Manufacturer Part": part.value,
                "Supplier": "LCSC / provisional",
                "Supplier Footprint": part.footprint,
                "Designator": f"{part.prefix}?",
                "Add into BOM": "yes",
                "Convert to PCB": "yes",
                "Symbol": part.symbol_uuid,
                "Footprint": part.footprint_uuid,
            },
        }, "dev-meta")

    def add_component(self, part: Part, designator: str, x: float, y: float,
                      attrs: dict[str, object]) -> str:
        comp_id = uid(f"component:{designator}")
        self.record("COMPONENT", {
            "partId": part.part_id, "x": x, "y": y, "rotation": 0,
            "isMirror": False, "attrs": {}, "zIndex": 100,
        }, comp_id)
        values = {
            "Symbol": part.symbol_uuid, "Device": part.device_uuid,
            "Designator": designator, "Value": part.value,
            "Footprint": part.footprint_uuid, "LCSC Part": part.lcsc,
        }
        values.update(attrs)
        for index, (key, value) in enumerate(values.items(), start=1):
            self.record("ATTR", self.attr_body(
                part.part_id, comp_id, key, value, index,
                value_visible=key in {"Designator", "Value"},
                x=x if key in {"Designator", "Value"} else None,
                y=y - 20 - index * 3 if key in {"Designator", "Value"} else None,
            ), uid(f"attr:{designator}:{key}"))
        return comp_id

    def add_wire(self, x1: float, y1: float, x2: float, y2: float,
                 net: str, label_x: float | None = None,
                 label_y: float | None = None) -> None:
        wire_id = uid(f"wire:{self.ticket}:{x1}:{y1}:{x2}:{y2}:{net}")
        self.record("WIRE", {"zIndex": 200}, wire_id)
        self.record("LINE", {
            "fillColor": None, "fillStyle": None, "strokeColor": None,
            "strokeStyle": None, "strokeWidth": None,
            "startX": x1, "startY": y1, "endX": x2, "endY": y2,
            "lineGroup": wire_id,
        }, uid(f"line:{wire_id}"))
        self.record("ATTR", self.attr_body(
            "", wire_id, "Relevance", "[]", 0), uid(f"relevance:{wire_id}"))
        self.record("ATTR", self.attr_body(
            "", wire_id, "NET", net, 2, value_visible=True,
            x=x1 if label_x is None else label_x,
            y=y1 if label_y is None else label_y), uid(f"net:{wire_id}"))

    def add_pin_net(self, part: Part, designator: str, x: float, y: float,
                    pin: Pin, net: str | None) -> None:
        if not net:
            return
        ax, ay = x + pin.x, y + pin.y
        if pin.rotation == 0:
            bx, by = ax - 35, ay
        elif pin.rotation == 180:
            bx, by = ax + 35, ay
        elif pin.rotation == 90:
            bx, by = ax, ay + 35
        else:
            bx, by = ax, ay - 35
        self.add_wire(ax, ay, bx, by, net, bx, by)

    def add_text(self, text: str, x: float, y: float, size: int = 12) -> None:
        # EasyEDA ignores unknown optional records safely; TEXT is used here
        # only for visible design notes and does not carry connectivity.
        self.record("TEXT", {
            "text": text, "x": x, "y": y, "rotation": 0,
            "fontSize": size, "fontFamily": "Arial", "fontWeight": False,
            "italic": False, "underline": False, "align": "LEFT_TOP",
            "color": None, "locked": False,
        }, uid(f"text:{x}:{y}:{text}"))

    def add_schematic(self, parts: list[Part]) -> None:
        sch_uuid = uid("section:SCH")
        page_uuid = uid("section:SCH_PAGE")
        self.dochead("SCH", sch_uuid)
        self.record("META", {"title": "Schematic1", "source": "",
                              "board": "", "zIndex": None}, "sch-meta")
        self.dochead("SCH_PAGE", page_uuid)
        self.record("META", {"title": PROJECT, "schematic": sch_uuid,
                              "source": "", "zIndex": 1}, "page-meta")

        by_name = {part.name: part for part in parts}
        placements: dict[str, tuple[str, str, float, float, dict[str, object]]] = {}

        def place(name: str, designator: str, x: float, y: float,
                  nets: dict[str, str | None], **attrs: object) -> None:
            part = by_name[name]
            self.add_component(part, designator, x, y, attrs)
            placements[designator] = (name, designator, x, y, attrs)
            for pin in part.pins:
                self.add_pin_net(part, designator, x, y, pin, nets.get(pin.number))

        place("TYPE-C16PIN_C393939", "J1", 180, -520, {
            "A1B12": "PD_GND", "A4B9": "VBUS_USB", "A5": "CC1",
            "A6": None, "A7": None, "A8": None, "B5": "CC2",
            "B6": None, "B7": None, "B8": None, "B4A9": "VBUS_USB",
            "B1A12": "PD_GND", "S1": "PD_GND", "S2": "PD_GND",
            "S3": "PD_GND", "S4": "PD_GND",
        })
        place("PTC_1206L110_30V_C49318383", "F1", 330, -585,
              {"1": "VBUS_USB", "2": "VBUS_RAW"})
        place("SMBJ24A_TVS_C41425647", "D1", 430, -350,
              {"1": "VBUS_RAW", "2": "PD_GND"})
        place("C_4U7_50V_C5246584", "C1", 510, -350,
              {"1": "VBUS_RAW", "2": "PD_GND"})
        place("C_100N_50V_C38141", "C2", 580, -350,
              {"1": "VBUS_RAW", "2": "PD_GND"})
        place("ESDA25W_CC1_C1974707", "D2", 360, -780,
              {"1": "CC1", "2": "PD_GND"})
        # Keep D3's CC2 stub away from D2's ground stub.  Overlapping stubs
        # would create a real short in the schematic even if their labels
        # were different.
        place("ESDA25W_CC2_C1974707", "D3", 550, -780,
              {"1": "CC2", "2": "PD_GND"})
        place("STUSB4500QTR_C2678061", "U1", 650, -520, {
            "1": "CC1", "2": "CC1", "3": None, "4": "CC2", "5": "CC2",
            "6": "RESET", "7": "SCL", "8": "SDA", "9": "DISCH_CTRL",
            "10": "PD_GND", "11": None, "12": "PD_GND", "13": "PD_GND",
            "14": None, "15": None, "16": "PMOS_GATE", "17": None,
            "18": "VBUS_RAW", "19": None, "20": None, "21": "PD_1V2",
            "22": "PD_GND", "23": "PD_2V7", "24": "VBUS_RAW", "25": "PD_GND",
        })
        place("AO3401A_C15127", "Q1", 900, -400,
              {"1": "VBUS_RAW", "2": "VBUS_SW", "3": "PMOS_GATE"})
        place("R_100K_C25803", "R1", 900, -280,
              {"1": "VBUS_RAW", "2": "PMOS_GATE"})
        place("R_1K_TBD", "R2", 800, -700,
              {"1": "DISCH_CTRL", "2": "VBUS_SW"})
        place("R_100K_RESET_C25803", "R6", 850, -980,
              {"1": "RESET", "2": "PD_GND"})
        place("R_4K7_C23162", "R7", 970, -1040,
              {"1": "SCL", "2": "PD_2V7"})
        place("R_4K7_C23162", "R8", 1220, -1040,
              {"1": "SDA", "2": "PD_2V7"})
        place("C_10U_50V_MODULE_TBD", "C11", 1000, -600,
              {"1": "VBUS_SW", "2": "PD_GND"})
        place("C_1U0_50V_MODULE_TBD", "C12", 1060, -600,
              {"1": "VBUS_SW", "2": "PD_GND"})
        place("C_1U0_VREG_TBD", "C3", 825, -850,
              {"1": "PD_1V2", "2": "PD_GND"})
        place("C_1U0_VREG_TBD", "C4", 935, -850,
              {"1": "PD_2V7", "2": "PD_GND"})
        place("WRB2405S-3WR2_C5369677", "U2", 1130, -430,
              {"1": "PD_GND", "2": "VBUS_SW", "3": None, "5": None,
               "6": "+5V", "7": "D_GND", "8": None})
        place("WRA2415S-3WR2_C5369663", "U3", 1130, -780,
              {"1": "PD_GND", "2": "VBUS_SW", "3": None, "5": None,
               "6": "+15V", "7": "A_GND", "8": "-15V"})
        place("C_100U_25V_TBD_1", "C5", 1300, -300,
              {"1": "+5V", "2": "D_GND"})
        place("C_100N_50V_TBD_1", "C6", 1380, -300,
              {"1": "+5V", "2": "D_GND"})
        place("R_160R_0V5_TBD", "R3", 1460, -300,
              {"1": "+5V", "2": "D_GND"})
        place("C_100U_25V_TBD_2", "C7", 1300, -620,
              {"1": "+15V", "2": "A_GND"})
        place("C_100N_50V_TBD_2", "C8", 1380, -620,
              {"1": "+15V", "2": "A_GND"})
        place("R_3K_0V5_A_PLUS_TBD", "R4", 1460, -620,
              {"1": "+15V", "2": "A_GND"})
        place("C_100U_25V_TBD_3", "C9", 1300, -900,
              {"1": "-15V", "2": "A_GND"})
        place("C_100N_50V_TBD_3", "C10", 1380, -900,
              {"1": "-15V", "2": "A_GND"})
        place("R_3K_0V5_A_MINUS_TBD", "R5", 1460, -900,
              {"1": "-15V", "2": "A_GND"})
        place("HDR5_CMU800", "J2", 1710, -500, {
            "1": "A_GND", "2": "-15V", "3": "+15V", "4": "D_GND", "5": "+5V",
        }, **{"Connector": "CN1-compatible"})
        place("HDR5_CMU800", "J3", 1710, -820, {
            "1": "A_GND", "2": "-15V", "3": "+15V", "4": "D_GND", "5": "+5V",
        }, **{"Connector": "CN3-compatible"})
        place("HDR5_STUSB_PROG", "J4", 1710, -1120, {
            "1": "VBUS_RAW", "2": "PD_GND", "3": "SCL", "4": "SDA", "5": "RESET",
        }, **{"Connector": "STUSB4500 I2C/NVM programming"})

        self.add_text("CMU-800 USB-PD replacement PSU", 100, -1050, 18)
        self.add_text("Request fixed 20 V PDO in STUSB4500 NVM before use", 100, -1015, 12)
        self.add_text("PD_GND / D_GND / A_GND are intentionally isolated domains", 100, -980, 12)
        self.add_text("J4: VDD, GND, SCL, SDA, RESET for NVM programming/test", 100, -945, 12)
        self.add_text("U2 CTRL and CS, U3 CTRL/NC are left open per module datasheet", 100, -910, 12)
        self.add_text("PCB outline and mounting holes: pending CMU-800 measurements", 100, -875, 12)

    def add_blob(self) -> None:
        self.dochead("BLOB", "BLOB")

    def build(self, parts: list[Part]) -> str:
        # Library order follows EasyEDA's normal generated order: symbol,
        # footprint, device, then schematic/page/blob.
        for part in parts:
            self.add_symbol(part)
            self.add_footprint(part)
            self.add_device(part)
        self.add_schematic(parts)
        self.add_blob()
        return "\n".join(self.lines) + "\n"


def project_json() -> str:
    return json.dumps({
        "title": PROJECT,
        "cbb_project": False,
        "editorVersion": "EasyEDA Pro v3 epru generated source",
        "introduction": "CMU-800 replacement PSU: USB-PD 20 V to isolated +5 V and +/-15 V.",
        "description": "Schematic source only; PCB is held until enclosure measurements are available.",
        "tags": ["CMU-800", "USB-PD", "power supply"],
    }, ensure_ascii=False, indent=2) + "\n"


def write_outputs() -> tuple[Path, Path]:
    parts = make_parts()
    epru = Epru()
    content = epru.build(parts)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    epru_path = OUT_DIR / f"{PROJECT}.epru"
    epro2_path = OUT_DIR / f"{PROJECT}.epro2"
    epru_path.write_text(content, encoding="utf-8")
    with zipfile.ZipFile(epro2_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("project2.json", project_json())
        archive.writestr(f"{PROJECT}.epru", content)
    print(f"generated {epru_path} ({len(epru.lines)} records, {epru.ticket - 1} tickets)")
    print(f"generated {epro2_path}")
    return epru_path, epro2_path


if __name__ == "__main__":
    write_outputs()
