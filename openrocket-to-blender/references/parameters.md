# Parameters Reference

## Complete `params` Dictionary Structure

```python
params = {
    # ===== Global =====
    "prefix":     "Rocket",       # Object name prefix (e.g. "Rocket_NoseCone")
    "segments":   48,             # Circumferential vertices (higher = rounder, 32-64 recommended)
    "scale":      0.001,          # mm → Blender units (1 BU = 1 m)
    "ellipse_slices": 48,         # Longitudinal slices for ellipsoid nose

    # ===== Nose Cone =====
    "nose": {
        "type":              "ellipsoid",  # "ellipsoid" | "conical"
        "length":            70.0,         # Length along Z-axis (mm)
        "base_radius_outer": 20.0,         # Base outer radius (mm)
        "wall":              2.0,          # Wall thickness (mm)
        "tip_radius_outer":  0.5,          # Min outer radius at tip (prevents non-manifold point)
        "tip_radius_inner":  0.2,          # Min inner radius at tip
        "mat":               "nose",       # Material key in materials dict
    },

    # ===== Body Tubes (multiple allowed) =====
    "body_tubes": [
        {
            "name":         "BodyTube1",   # Suffix for object name
            "length":       170.0,         # Length along Z-axis (mm)
            "radius_outer": 20.0,          # Outer radius (mm)
            "wall":         2.0,           # Wall thickness (mm)
            "mat":          "body",        # Material key
        },
        # ... additional body tubes
    ],

    # ===== Conical Transitions (multiple allowed) =====
    "transitions": [
        {
            "name":               "Transition",
            "length":             50.0,         # Length along Z-axis (mm)
            "radius_front_outer": 20.0,         # Front-end outer radius
            "radius_rear_outer":  12.5,         # Rear-end outer radius
            "wall":               2.0,          # Wall thickness (mm)
            "mat":                "transition",
        },
        # ... additional transitions
    ],

    # ===== Trapezoidal Fins =====
    "fins": {
        "count":      4,          # Number of blades (evenly distributed around Z-axis)
        "root_chord": 25.0,       # Root chord length (mm)
        "tip_chord":  12.0,       # Tip chord length (mm)
        "height":     50.0,       # Span (from body outer wall outward) (mm)
        "sweep":      40.0,       # Sweep distance (mm)
        "thickness":  1.0,        # Fin thickness (mm)
        "mat":        "fins",
    },

    # ===== Material Colors =====
    "materials": {
        "nose":       (0.85, 0.35, 0.10),  # Orangish-red
        "body":       (0.92, 0.92, 0.92),  # Light gray
        "body2":      (0.80, 0.80, 0.80),  # Medium gray
        "transition": (0.25, 0.50, 0.85),  # Blue
        "fins":       (0.12, 0.12, 0.18),  # Dark gray
    },
}
```

## Z-Axis Layout

Parts are stacked along **+Z** in this order: **nose → body_tubes ↔ transitions → fins**

```
Z=0       ─── Nose cone tip (small disk cap)
Z=L_nose  ─── Nose base / BodyTube1 top
  ...     ─── Segments stacked sequentially
Z=end     ─── Last body tube bottom / fin root trailing edge
```

**Segment count rule**: `body_tubes` has exactly one more element than `transitions`.
Example: `body_tubes=[BT1, BT2]` + `transitions=[TR1]` → BT1 → TR1 → BT2 → fins

## Ellipsoid Nose Cone Formula

```
r(z) = R × √( 1 - ((z - L) / L)² )

Where: L = nose cone length, R = base radius, z ∈ [0, L]
       z=0 → r→0 (tip),   z=L → r=R (base)
```

Internally uses 48 longitudinal slices. Adjacent slices connected with quad strips.
Tip capped with a tiny flat disk (min_radius) to prevent non-manifold vertex convergence.

## Watertight Guarantee

| Part        | Strategy                                                                 |
|-------------|--------------------------------------------------------------------------|
| Tube/Cone   | `build_shell`: outer + inner + top ring + bottom ring, each edge shared by 2 faces |
| Ellipsoid   | 48-slice multi-ring: outer + inner surface + tip cap + base ring         |
| Fins        | 8 vertices → 6 closed faces (bottom + top + leading + trailing + root + tip) |
| Global      | `remove_doubles` + `recalc_face_normals` on every part                   |

## Sweep Angle Calculation

```
sweep_angle = atan(sweep_distance / fin_height)

Example: sweep=40mm, height=50mm → atan(40/50) = 38.7°
```
