#!/usr/bin/env python3
"""Static checks for the generated EasyEDA Pro project.

This is intentionally independent of the EasyEDA bridge.  It checks the
portable parts of the epru format: record syntax, monotonically increasing
tickets, section references, component attributes, wire groups, pin stubs,
and accidental intersections between differently named nets.
"""

from __future__ import annotations

import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path


REQUIRED_SECTIONS = {"DEVICE", "SYMBOL", "FOOTPRINT", "SCH", "SCH_PAGE", "BLOB"}
EXPECTED_NC = {
    "J1": {"A6", "A7", "A8", "B6", "B7", "B8"},
    "U1": {"3", "11", "14", "15", "17", "19", "20"},
    "U2": {"3", "5", "8"},
    "U3": {"3", "5"},
}

EXPECTED_NETS = {
    "F1": {"1": "VBUS_USB", "2": "VBUS_RAW"},
    "D1": {"1": "VBUS_RAW", "2": "PD_GND"},
    "D2": {"1": "CC1", "2": "PD_GND"},
    "D3": {"1": "CC2", "2": "PD_GND"},
    "U1": {"1": "CC1", "2": "CC1", "4": "CC2", "5": "CC2",
           "6": "RESET", "7": "SCL", "8": "SDA", "9": "DISCH_CTRL",
           "10": "PD_GND", "12": "PD_GND", "13": "PD_GND",
           "16": "PMOS_GATE", "18": "VBUS_RAW", "21": "PD_1V2",
           "22": "PD_GND", "23": "PD_2V7", "24": "VBUS_RAW", "25": "PD_GND"},
    "Q1": {"1": "VBUS_RAW", "2": "VBUS_SW", "3": "PMOS_GATE"},
    "U2": {"1": "PD_GND", "2": "VBUS_SW", "6": "+5V", "7": "D_GND"},
    "U3": {"1": "PD_GND", "2": "VBUS_SW", "6": "+15V", "7": "A_GND", "8": "-15V"},
    "J2": {"1": "A_GND", "2": "-15V", "3": "+15V", "4": "D_GND", "5": "+5V"},
    "J3": {"1": "A_GND", "2": "-15V", "3": "+15V", "4": "D_GND", "5": "+5V"},
    "J4": {"1": "VBUS_RAW", "2": "PD_GND", "3": "SCL", "4": "SDA", "5": "RESET"},
}


def parse_line(line: str) -> tuple[dict, dict]:
    parts = line.rstrip("\n").split("||")
    if len(parts) != 2:
        raise ValueError("record does not contain exactly one || separator")
    body_text = parts[1]
    if not body_text.endswith("|"):
        raise ValueError("record does not end with |")
    return json.loads(parts[0]), json.loads(body_text[:-1])


def load(path: Path) -> tuple[list[tuple[dict, dict]], str, str]:
    if path.suffix == ".epro2":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if "project2.json" not in names:
                raise ValueError("project2.json missing from archive")
            epru_names = [name for name in names if name.endswith(".epru")]
            if len(epru_names) != 1:
                raise ValueError(f"expected one .epru, found {epru_names}")
            project = archive.read("project2.json").decode("utf-8")
            epru_name = epru_names[0]
            content = archive.read(epru_name).decode("utf-8")
        return [parse_line(line) for line in content.splitlines() if line.strip()], content, project
    content = path.read_text(encoding="utf-8")
    return [parse_line(line) for line in content.splitlines() if line.strip()], content, ""


def sections(records: list[tuple[dict, dict]]) -> dict[str, int]:
    found: dict[str, int] = {}
    for index, (header, body) in enumerate(records):
        if header.get("type") == "DOCHEAD":
            found[body.get("docType", "")] = found.get(body.get("docType", ""), 0) + 1
    return found


def section_records(records: list[tuple[dict, dict]]) -> dict[str, list[tuple[dict, dict]]]:
    result: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    current = ""
    for header, body in records:
        if header.get("type") == "DOCHEAD":
            current = body.get("docType", "")
        result[current].append((header, body))
    return result


def orientation(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> float:
    return (by - ay) * (cx - bx) - (bx - ax) * (cy - by)


def on_segment(ax: float, ay: float, bx: float, by: float, px: float, py: float) -> bool:
    return min(ax, bx) <= px <= max(ax, bx) and min(ay, by) <= py <= max(ay, by)


def segments_touch(a: tuple[float, float, float, float],
                   b: tuple[float, float, float, float]) -> bool:
    ax, ay, bx, by = a
    cx, cy, dx, dy = b
    o1 = orientation(ax, ay, bx, by, cx, cy)
    o2 = orientation(ax, ay, bx, by, dx, dy)
    o3 = orientation(cx, cy, dx, dy, ax, ay)
    o4 = orientation(cx, cy, dx, dy, bx, by)
    eps = 1e-9
    if (o1 * o2 < -eps and o3 * o4 < -eps):
        return True
    if abs(o1) <= eps and on_segment(ax, ay, bx, by, cx, cy):
        return True
    if abs(o2) <= eps and on_segment(ax, ay, bx, by, dx, dy):
        return True
    if abs(o3) <= eps and on_segment(cx, cy, dx, dy, ax, ay):
        return True
    if abs(o4) <= eps and on_segment(cx, cy, dx, dy, bx, by):
        return True
    return False


def main(path_text: str) -> int:
    path = Path(path_text)
    try:
        records, content, project = load(path)
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"FAIL: {exc}")
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    tickets = [header.get("ticket") for header, _ in records]
    expected_tickets = list(range(1, len(records) + 1))
    if tickets != expected_tickets:
        errors.append("tickets are not consecutive starting at 1")
    # EasyEDA scopes record IDs to their document section; library sections
    # legitimately reuse IDs such as META and pin-1.
    ids_by_section: dict[str, set[str]] = defaultdict(set)
    current_section = ""
    for header, body in records:
        if header.get("type") == "DOCHEAD":
            current_section = f"{body.get('docType', '')}:{body.get('uuid', '')}"
        record_id = header.get("id")
        if record_id is not None:
            if record_id in ids_by_section[current_section]:
                errors.append(f"duplicate record id {record_id} in {current_section}")
            ids_by_section[current_section].add(record_id)

    found_sections = sections(records)
    missing = REQUIRED_SECTIONS - set(found_sections)
    if missing:
        errors.append(f"missing sections: {', '.join(sorted(missing))}")
    for name, count in found_sections.items():
        if count > 1 and name in {"SCH", "SCH_PAGE", "BLOB"}:
            errors.append(f"unexpected duplicate {name} section")

    by_section = section_records(records)
    symbol_uuids = {
        body.get("uuid") for header, body in records
        if header.get("type") == "DOCHEAD" and body.get("docType") == "SYMBOL"
    }
    footprint_uuids = {
        body.get("uuid") for header, body in records
        if header.get("type") == "DOCHEAD" and body.get("docType") == "FOOTPRINT"
    }
    device_attrs: dict[str, dict] = {}
    current_device = None
    for header, body in records:
        if header.get("type") == "DOCHEAD":
            current_device = body.get("uuid") if body.get("docType") == "DEVICE" else None
        elif current_device and header.get("type") == "META":
            device_attrs[current_device] = body.get("attributes", {})
    for device_uuid, attrs in device_attrs.items():
        if attrs.get("Symbol") not in symbol_uuids:
            errors.append(f"device {device_uuid} references missing symbol")
        if attrs.get("Footprint") not in footprint_uuids:
            errors.append(f"device {device_uuid} references missing footprint")

    page = by_section.get("SCH_PAGE", [])
    components: dict[str, dict] = {}
    for header, body in page:
        if header.get("type") == "COMPONENT":
            components[header["id"]] = body
    attrs_by_parent: dict[str, dict[str, object]] = defaultdict(dict)
    for header, body in page:
        if header.get("type") == "ATTR" and body.get("parentId"):
            attrs_by_parent[body["parentId"]][body.get("key", "")] = body.get("value")
    designators: set[str] = set()
    for comp_id, body in components.items():
        attrs = attrs_by_parent[comp_id]
        for key in ("Symbol", "Device", "Designator", "Footprint"):
            if key not in attrs:
                errors.append(f"component {comp_id} missing {key} attribute")
        if attrs.get("Symbol") not in symbol_uuids:
            errors.append(f"component {attrs.get('Designator', comp_id)} references missing symbol")
        if attrs.get("Device") not in device_attrs:
            errors.append(f"component {attrs.get('Designator', comp_id)} references missing device")
        designator = str(attrs.get("Designator", ""))
        if designator in designators:
            errors.append(f"duplicate designator {designator}")
        designators.add(designator)

    wires: dict[str, dict] = {}
    for header, body in page:
        typ = header.get("type")
        if typ == "WIRE":
            wires[header["id"]] = {"net": "", "segments": []}
        elif typ == "LINE" and body.get("lineGroup") in wires:
            wires[body["lineGroup"]]["segments"].append(
                (body.get("startX"), body.get("startY"), body.get("endX"), body.get("endY")))
        elif typ == "ATTR" and body.get("parentId") in wires and body.get("key") == "NET":
            wires[body["parentId"]]["net"] = body.get("value", "")
    if not wires:
        errors.append("schematic contains no wires")
    if any(not wire["segments"] for wire in wires.values()):
        errors.append("one or more WIRE records have no LINE")
    net_names = {wire["net"] for wire in wires.values()}
    for isolated in ("PD_GND", "D_GND", "A_GND"):
        if isolated not in net_names:
            errors.append(f"required isolated net {isolated} is missing")
    if {"PD_GND", "D_GND", "A_GND"}.issubset(net_names):
        print("isolated domains present: PD_GND, D_GND, A_GND")

    # Detect true geometric shorts between differently named stubs.  A same-net
    # intersection is harmless and expected when a net is drawn continuously.
    named_wires = [(wid, wire["net"], segment)
                   for wid, wire in wires.items() if wire["net"]
                   for segment in wire["segments"]]
    for index, (wid_a, net_a, seg_a) in enumerate(named_wires):
        for wid_b, net_b, seg_b in named_wires[index + 1:]:
            if net_a != net_b and segments_touch(seg_a, seg_b):
                errors.append(f"different nets intersect: {net_a} ({wid_a}) / {net_b} ({wid_b})")

    # Every non-NC pin in the generated design must have a wire endpoint.  This
    # catches accidental coordinate drift in the generator.  A future EasyEDA
    # editing pass can replace NC omissions with explicit no-connect markers.
    symbols: dict[str, list[dict]] = defaultdict(list)
    current_symbol = None
    current_pin = None
    for header, body in records:
        if header.get("type") == "DOCHEAD":
            current_symbol = body.get("uuid") if body.get("docType") == "SYMBOL" else None
            current_pin = None
        elif current_symbol and header.get("type") == "PIN":
            current_pin = {"number": "", "x": body.get("x"), "y": body.get("y")}
            symbols[current_symbol].append(current_pin)
        elif current_symbol and current_pin and header.get("type") == "ATTR":
            if body.get("key") == "Pin Number":
                current_pin["number"] = str(body.get("value"))

    wire_endpoints = {(x1, y1) for wire in wires.values() for x1, y1, x2, y2 in wire["segments"]}
    wire_endpoints |= {(x2, y2) for wire in wires.values() for x1, y1, x2, y2 in wire["segments"]}
    endpoint_nets: dict[tuple[float, float], set[str]] = defaultdict(set)
    for wire in wires.values():
        for x1, y1, x2, y2 in wire["segments"]:
            endpoint_nets[(x1, y1)].add(wire["net"])
            endpoint_nets[(x2, y2)].add(wire["net"])
    for comp_id, body in components.items():
        attrs = attrs_by_parent[comp_id]
        designator = str(attrs.get("Designator", ""))
        symbol_pins = symbols.get(attrs.get("Symbol"), [])
        for pin in symbol_pins:
            if pin["number"] in EXPECTED_NC.get(designator, set()):
                continue
            absolute = (body.get("x") + pin["x"], body.get("y") + pin["y"])
            if absolute not in wire_endpoints:
                errors.append(f"unwired pin {designator}.{pin['number']}")
        for pin_number, expected_net in EXPECTED_NETS.get(designator, {}).items():
            matching = [pin for pin in symbol_pins if pin["number"] == pin_number]
            if not matching:
                errors.append(f"expected pin {designator}.{pin_number} is missing from symbol")
                continue
            pin = matching[0]
            absolute = (body.get("x") + pin["x"], body.get("y") + pin["y"])
            if expected_net not in endpoint_nets.get(absolute, set()):
                actual = sorted(endpoint_nets.get(absolute, set()))
                errors.append(f"wrong net {designator}.{pin_number}: expected {expected_net}, got {actual}")

    # Archive/source identity check is useful when the packaged project is
    # regenerated after editing the plain source.
    if path.suffix == ".epro2":
        with zipfile.ZipFile(path) as archive:
            epru_name = next(name for name in archive.namelist() if name.endswith(".epru"))
            source = path.with_name(epru_name)
            if source.exists() and source.read_text(encoding="utf-8") != content:
                errors.append("archive epru differs from adjacent source epru")
    if project:
        try:
            project_data = json.loads(project)
            if project_data.get("title") != "CMU800_USB_PD_Power_Unit":
                errors.append("project title mismatch")
        except json.JSONDecodeError:
            errors.append("project2.json is not JSON")

    print(f"records: {len(records)}; sections: {dict(sorted(found_sections.items()))}")
    print(f"components: {len(components)}; wires: {len(wires)}; nets: {len(net_names)}")
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        return 1
    print("PASS: EasyEDA Pro project passed static checks")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} FILE.epro2|FILE.epru")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
