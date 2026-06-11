# OpenRocket → Blender

[![Blender](https://img.shields.io/badge/Blender-3.x+-orange)](https://www.blender.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.x-blue)](https://www.python.org/)

Convert [OpenRocket](https://openrocket.info/) rocket design parameters into **watertight, 3D-printable Blender models** in one step. Zero external dependencies — pure `bpy` + `bmesh`.

## What It Does

Takes a parameter dictionary (nose cone, body tubes, transitions, fins — all in mm) and generates standalone Blender objects:

- **Ellipsoid or conical nose cones** — 48-slice multi-ring construction, tiny flat tip cap (no non-manifold points)
- **Thin-walled body tubes** — inner + outer faces + annular end caps
- **Conical transitions** — tapered transition sections between different tube diameters
- **Trapezoidal fins** — N blades evenly distributed around Z-axis, adjustable sweep angle

Every part is **mathematically watertight**: each edge shared by exactly 2 faces → ready for slicing and 3D printing.

## Quick Start

Copy `scripts/rocket_builder.py` into Blender's Scripting workspace and run:

```python
from rocket_builder import build_rocket

params = {
    "prefix": "MyRocket",
    "nose": {
        "type": "ellipsoid",
        "length": 70, "base_radius_outer": 20, "wall": 2,
    },
    "body_tubes": [
        {"name": "Body1", "length": 170, "radius_outer": 20, "wall": 2},
        {"name": "Body2", "length": 73,  "radius_outer": 12.5, "wall": 3.5},
    ],
    "transitions": [
        {"name": "Transition1", "length": 50,
         "radius_front_outer": 20, "radius_rear_outer": 12.5, "wall": 2},
    ],
    "fins": {
        "count": 4, "root_chord": 25, "tip_chord": 12,
        "height": 50, "sweep": 40, "thickness": 1,
    },
}
build_rocket(params)
```

Or paste the generated standalone script directly into the Blender console.

## File Structure

```
openrocket-to-blender/
├── README.md
├── SKILL.md                          # AI assistant prompt template
├── scripts/
│   └── rocket_builder.py             # Core builder module
└── references/
    └── parameters.md                 # Full parameter reference
```

## Parameters

All dimensions in **millimeters**. Internal scaling to Blender units (1 BU = 1 m) is handled automatically.

| Parameter | Type | Description |
|-----------|------|-------------|
| `nose.type` | `"ellipsoid"` or `"conical"` | Nose cone shape |
| `nose.length` | float | Nose length along Z (mm) |
| `nose.base_radius_outer` | float | Nose base outer radius (mm) |
| `nose.wall` | float | Wall thickness (mm) |
| `body_tubes[i].length` | float | Tube length (mm) |
| `body_tubes[i].radius_outer` | float | Outer radius (mm) |
| `body_tubes[i].wall` | float | Wall thickness (mm) |
| `transitions[i].length` | float | Transition length (mm) |
| `fins.count` | int | Number of fin blades |
| `fins.root_chord` | float | Root chord length (mm) |
| `fins.tip_chord` | float | Tip chord length (mm) |
| `fins.height` | float | Fin span from body wall (mm) |
| `fins.sweep` | float | Sweep distance (mm) |

See `references/parameters.md` for the complete parameter dictionary.

## Nose Cone Math

**Ellipsoid** (half-ellipsoid):
```
r(z) = R × sqrt(1 - ((z - L) / L)^2)
```
48 longitudinal slices, adjacent rings connected with quad strips. Tip sealed with a small flat disk (r ≈ 0.5 mm).

## Watertight Guarantee

| Part | Method |
|------|--------|
| Tube / Cone | `build_shell`: outer + inner + top ring + bottom ring |
| Ellipsoid | 48-slice multi-ring: outer surface + inner surface + tip cap + base ring |
| Fins | 8 vertices → 6 closed quad faces |
| All parts | `remove_doubles` + `recalc_face_normals` |

## Dependencies

- [Blender](https://www.blender.org/) 3.x or later (built-in `bpy` + `bmesh`)

No pip installs, no external packages.

## License

MIT
