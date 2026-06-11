---
name: openrocket-to-blender
description: "Convert OpenRocket rocket design parameters into watertight Blender 3D-printable models. This skill should be used when the user provides rocket geometry specs (nose cone, body tubes, transitions, fins) and wants a Blender Python script to generate STL-slicable parts. Triggers: OpenRocket to Blender, rocket model, 3D print rocket, rocket blender script, or detailed rocket segment dimensions in millimeters."
agent_created: true
---

# OpenRocket → Blender Rocket Modeling

Converts OpenRocket rocket design parameters into Blender 3D-printable models in one step.

## Core Capabilities

- **Ellipsoid / truncated-cone nose cones** — multi-slice construction guarantees watertight geometry
- **Thin-walled body tubes** — inner/outer surfaces plus annular end caps, fully sealed
- **Conical transitions** — matches different front and rear tube diameters
- **Trapezoidal fins** (N blades, evenly distributed) — adjustable sweep angle
- **Mathematically watertight parts** — every edge shared by exactly 2 faces
- **Pure bpy + bmesh** — zero external dependencies, paste directly into Blender Scripting console

## When to Use

- User provides rocket dimension specs (nose, body tubes, transitions, fins)
- User says "convert OpenRocket data to Blender model"
- User needs 3D-printable rocket STL files
- User mentions "write Blender script" + rocket geometry parameters
- User attaches an OpenRocket screenshot with labeled dimensions

## Workflow

### 1. Collect Parameters

Extract a params dictionary from the user's description. All units in **millimeters**.
Full parameter reference: `references/parameters.md`.

Minimum required parameters:
- `nose`: type (`ellipsoid` or `conical`), `length`, `base_radius_outer`, `wall`
- `body_tubes`: list of `{length, radius_outer, wall}`
- `transitions` (optional): list of `{length, radius_front_outer, radius_rear_outer, wall}`
- `fins`: `{count, root_chord, tip_chord, height, sweep, thickness}`

### 2. Generate Script

Generate a **standalone `.py` file** for Blender's Scripting console. Do NOT modify `scripts/rocket_builder.py` — instead produce a self-contained script with everything inlined.

Required content:
1. **Hardcoded parameters** with comments noting their source
2. **Five core geometry functions**: `ring()`, `quad_ring()`, `quad_ring_inner()`, `cap_ring()`, `build_shell()`
3. **Part builder functions**: ellipsoid nose (multi-slice), conical nose, body tube, transition, fins
4. **`finalize()`** — bmesh → Blender object (applies SCALE, remove_doubles, recalc_normals)
5. **`make_mat()`** — Principled BSDF material (searches by `bl_idname`, compatible with Chinese/English Blender UI)
6. **Z-axis positioning + parameter verification printout**

After writing the script:
- Run `python -m py_compile` to catch syntax errors
- Verify every OD/ID/wall/length against user input
- Confirm fin root trailing edge aligns with body tube bottom

### 3. Critical Constraints (Must Follow)

- **Never use Blender native cone/cylinder primitives** — build everything from scratch with bmesh to avoid non-manifold geometry
- **No sharp tip on nose cone** — ellipsoid nose tip min radius ≥ 0.5mm (tiny flat disk cap)
- **All `obj.location` = (0, 0, 0)** — vertex Z coordinates are absolute, no offset needed
- **Apply SCALE inside `finalize()`** on every vertex — never use `bpy.ops.transform_apply`
- **Every edge shared by exactly 2 faces** — this is the necessary and sufficient condition for watertightness

### 4. Blender Pitfalls (Built into `scripts/rocket_builder.py`)

Already handled in the code:
- `ShaderNodeMaterialOutput` → find BSDF node by `bl_idname` type, not hardcoded name
- `apply_scale` bpy.ops → modify `vertex.co` directly instead
- Material node name differences → compatible with Chinese and English Blender UI

## Ellipsoid Nose Multi-Slice Method

Half-ellipsoid formula: `r(z) = R × sqrt(1 - ((z-L)/L)^2)`
where L = nose length, R = base radius.

Implementation: sample N slices along Z-axis, generate outer + inner vertex rings at each slice, connect adjacent slices with quad strips, cap the tip with `cap_ring`. See `references/parameters.md` for full math derivation.

## Script Structure Template

Generated scripts follow this structure:
1. File header comment (parameter source + Z-axis layout)
2. Global parameters (hardcoded)
3. Five core geometry functions
4. Part builder functions
5. `finalize()` + `make_mat()`
6. Material creation
7. Main flow: build → finalize → position → report

## References

- `references/parameters.md` — complete parameter dictionary structure and Z-axis layout
- `scripts/rocket_builder.py` — core builder module (copy snippets from, do not import directly)
