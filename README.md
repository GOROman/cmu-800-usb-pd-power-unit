# CMU-800 USB-PD power unit

USB-C Power Delivery入力から、AMDEK/Roland DG CMU-800の電源コネクタへ
`+5 V / D-GND / +15 V / -15 V / A-GND`を供給する交換用電源ユニットの
回路図実装です。

Status: **schematic implementation / review candidate**. EasyEDA Proの回路図
ソースと`.epro2`パッケージは生成済みですが、CMU-800本体の基板外形・取付穴・
コネクタ位置を実測していないため、PCBと製造データはまだリリースしていません。

## Files

- [EasyEDA Pro package](easyeda/CMU800_USB_PD_Power_Unit.epro2)
- [EasyEDA Pro epru source](easyeda/CMU800_USB_PD_Power_Unit.epru)
- [Deterministic generator](tools/generate_epro2.py)
- [Static verifier](tools/verify_epro2.py)
- [BOM](docs/BOM.csv)
- [CMU-800 research and schematic review](docs/CMU-800-RESEARCH.md)
- [PCB release gate](pcb/README.md)

Regenerate and statically verify:

```sh
python3 tools/generate_epro2.py
python3 tools/verify_epro2.py easyeda/CMU800_USB_PD_Power_Unit.epro2
```

The generated schematic was also read by the EasyEDA Pro format parser: 32
components, 103 wire records, 32 library symbols, and 18 named nets.

## Electrical architecture

```text
USB-C receptacle
      │  VBUS / CC1 / CC2
      ├─ F1 + TVS + input capacitors ─ VBUS_RAW ─┐
      │                                           │
      └─ STUSB4500QTR ─ VBUS_EN_SNK ─ AO3401A ─ VBUS_SW
                                                   ├─ WRB2405S-3WR2 ─ +5V / D-GND
                                                   └─ WRA2415S-3WR2 ─ +15V / A-GND / -15V
```

The new design replaces the original mains transformer, rectifiers, and
`7805/7815/7915` linear regulators. The isolated `WRA2415S-3WR2` produces the
nominal `+15 V` and `-15 V` rails directly, so the old 7815/7915 stages are not
copied. `WRB2405S-3WR2` produces the isolated digital `+5 V` rail.

`PD_GND`, `D_GND`, and `A_GND` are separate net names and are not joined on this
board. The two isolated converter outputs retain their own isolated return
domains. This is the intended analogue/digital isolation model, not a claim
that an installed module has zero parasitic capacitance.

## CMU-800 output connector pinout

The public service schematic labels both `CN1` and `CN3` with the same five-pin
assignment:

| Pin | Signal | New-board net |
|---:|---|---|
| 1 | A-GND | `A_GND` |
| 2 | -15 V | `-15V` |
| 3 | +15 V | `+15V` |
| 4 | D-GND | `D_GND` |
| 5 | +5 V | `+5V` |

J2 and J3 in the design are placeholders for those two mating connectors.
Their pitch, keying, height, and cable orientation must be checked against the
actual CMU-800 before a PCB footprint is released.

## Important bring-up constraints

1. The STUSB4500 is an autonomous sink, but its NVM must be configured with a
   fixed 20 V PDO before expecting `VBUS_SW` to power the converters. J4 exposes
   `VDD / PD_GND / SCL / SDA / RESET` for programming and test; the schematic
   does not contain the NVM configuration data itself.
2. The WRA/WRB modules are nominal 24 V-input parts with an 18 V minimum input.
   A compliant 20 V PD contract is inside that range but leaves only 2 V of
   margin. Validate long cables, source current limits, startup, and load
   transients before connecting a CMU-800.
3. R3 is a 160 ohm, at least 0.5 W bleed load for the 5 V converter. R4 and R5
   are 3.0 kohm, at least 0.5 W bleeds for the positive and negative 15 V rails.
   These are present to satisfy the converter minimum-load requirement and are
   not substitutes for measuring the CMU-800 load.
4. The first power-up should be performed with a current-limited USB-PD source,
   with the CMU-800 disconnected. Check `+5 V`, `+15 V`, `-15 V`, the three
   return domains, ripple, and temperature before applying the output cables.
5. This is a low-voltage replacement input, not a mains-connected circuit. Do
   not connect the USB-C input to any original mains wiring.

## Validation boundary

The current validation is static: JSON/epru syntax, package structure, library
references, component attributes, pin-stub coverage, and accidental
intersections between differently named nets. EasyEDA Pro was not connected to
this session, and no PCB was fabricated or tested on a physical CMU-800 yet.

## Primary references

- [CMU-800 service schematic](https://synthfool.com/docs/Roland/Roland_CMU800_Schematic.pdf)
- [E&MM Micromusic CMU-800 article](https://www.muzines.co.uk/articles/micromusic/5882)
- [STUSB4500QTR datasheet](https://www.st.com/resource/en/datasheet/stusb4500.pdf)
- [MORNSUN WRA2415S-3WR2 product page](https://www.mornsun-power.com/index/sitesearch/partlink/keyword/WRA2415S-3WR2.html)
- [MORNSUN WRB2405S-3WR2 listing](https://www.mornsun-power.com/html/products-detail/WRB_S-3WR2.html)
