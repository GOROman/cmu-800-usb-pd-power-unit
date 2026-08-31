# PCB release gate

The PCB is intentionally not generated yet.  The schematic contains placeholder
footprint attachments so it can be opened and reviewed in EasyEDA Pro, but no
board outline or mounting geometry is claimed.

Before making a JLCPCB order, capture and record:

- original PSU board outline and thickness;
- mounting-hole centers, diameters, edge clearances, and screw keep-outs;
- CN1/CN3 connector manufacturer/series, pitch, keying, height, and pin-1
  orientation;
- cable/harness exit direction and enclosure clearances;
- transformer clearance and any chassis shield or earth hardware that must be
  removed or retained;
- whether the replacement board is mechanically supported by the original
  standoffs or needs a printed carrier.

The release sequence is: measured drawing → EasyEDA footprints/board outline →
ERC/DRC → 1-board prototype → current-limited bring-up → CMU-800 connection →
JLCPCB production files.  Do not treat the current `.epro2` as Gerber, drill,
pick-and-place, or a fabrication release.
