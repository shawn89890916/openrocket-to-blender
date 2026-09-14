# OpenRocket → Blender

[![Blender](https://img.shields.io/badge/Blender-3.x+-orange)](https://www.blender.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.x-blue)](https://www.python.org/)

Build closed-manifold, 3D-printable rocket parts in Blender from dimensions transcribed from an [OpenRocket](https://openrocket.info/) design. Zero external dependencies — pure `bpy` + `bmesh`.

> This project currently accepts a Python parameter dictionary. It does not parse `.ork` files. OpenRocket 23.09 and later already provide an official OBJ exporter for direct model transfer; this builder is useful when you want Blender-native, dimension-driven geometry with explicit wall thickness.

## What It Does

Takes a parameter dictionary (nose cone, body tubes, transitions, fins — all in mm) and generates standalone Blender objects:

- **Ellipsoid or conical nose cones** — 48-slice multi-ring construction, tiny flat tip cap (no non-manifold points)
- **Thin-walled body tubes** — inner + outer faces + annular end caps
- **Conical transitions** — tapered transition sections between different tube diameters
- **Trapezoidal fins** — N blades evenly distributed around Z-axis, adjustable sweep angle

Each generated part is a closed two-manifold mesh: every edge is shared by exactly two faces. The included Blender regression test checks this property. Run your slicer's geometry checks before manufacturing because manifold topology alone does not detect every possible self-intersection or invalid design dimension.

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

Or paste the generated standalone script directly into the Blender console. Invalid dimensions such as a wall that is as thick as its outer radius are rejected before any Blender objects are created.

## Choosing the Right Workflow

- Use OpenRocket's built-in `File > Export as > Wavefront OBJ` for a faithful transfer of a complete `.ork` design, including component placement and optional appearances.
- Use this builder when you have a small supported design and want separate Blender-native shell objects generated from a concise dimension dictionary.
- This version supports ellipsoid/conical nose cones, body tubes, conical transitions, and trapezoidal fins. Pods, parallel stages, freeform fins, rail buttons, motors, decals, and direct `.ork` import are outside the current scope.

## File Structure

```
openrocket-to-blender/
├── README.md
├── LICENSE
├── SKILL.md                          # AI assistant prompt template
├── tests/
│   └── blender_test.py               # Headless Blender regression tests
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
The number of longitudinal slices is configurable with `ellipse_slices`. Adjacent rings are connected with quad strips. The tip is sealed with a small flat disk (r ≈ 0.5 mm by default).

## Watertight Guarantee

| Part | Method |
|------|--------|
| Tube / Cone | `build_shell`: outer + inner + top ring + bottom ring |
| Ellipsoid | 48-slice multi-ring: outer surface + inner surface + tip cap + base ring |
| Fins | 8 vertices → 6 closed quad faces |
| All parts | Parameter validation + `remove_doubles` + `recalc_face_normals` |

## Tests

Run the regression suite inside Blender so it uses Blender's real `bpy` and `bmesh` implementations:

```powershell
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python tests/blender_test.py
```

The suite verifies closed-manifold topology, configurable ellipsoid resolution, documented minimum nose parameters, invalid wall rejection, and material reuse across rebuilds.

## Dependencies

- [Blender](https://www.blender.org/) 3.x or later (built-in `bpy` + `bmesh`)

No pip installs, no external packages.

## License

[MIT](LICENSE)
