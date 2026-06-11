"""
OpenRocket → Blender 火箭模型构建器
=====================================
将 OpenRocket 设计参数转化为 Blender 3D 打印模型。

所有几何体用 bmesh 从零构建（四圈顶点法 + 多切片椭圆体），
每条边恰好被 2 个面共享 — 数学保证流形(watertight)，可直接切片打印。

用法:
    # 在 Blender 控制台粘贴运行
    import sys
    sys.path.append(r"C:\path\to\skill\scripts")
    from rocket_builder import build_rocket
    
    params = { ... }
    build_rocket(params)

    # 或直接运行本脚本（需在 Blender 内执行）
    python rocket_builder.py

依赖: Blender 内置 bpy + bmesh (无需 pip install)
"""

import bpy
import bmesh
import math

__version__ = "1.0.0"
__all__ = [
    "ring", "quad_ring", "quad_ring_inner", "cap_ring",
    "build_shell", "make_ellipsoid_nose", "make_conical_nose",
    "make_body_tube", "make_transition", "make_fins",
    "finalize", "make_mat", "build_rocket", "DEFAULT_PARAMS",
]


# ================================================================
# 默认参数 (演示用 V5 火箭)
# ================================================================
DEFAULT_PARAMS = {
    "prefix":           "Rocket",
    "segments":         48,       # 圆周分段
    "scale":            0.001,    # mm → Blender 单位
    "ellipse_slices":   48,       # 椭圆体头锥纵向切片数
    "nose": {
        "type":                 "ellipsoid",   # "ellipsoid" | "conical"
        "length":               70.0,
        "base_radius_outer":    20.0,          # 底座外半径 Ø40/2
        "wall":                 2.0,
        "tip_radius_outer":     0.5,           # 尖端最小半径 (避免非流形点)
        "tip_radius_inner":     0.2,
    },
    "body_tubes": [
        {
            "name":          "BodyTube1",
            "length":        170.0,
            "radius_outer":  20.0,
            "wall":          2.0,
            "mat":           "body",
        },
        {
            "name":          "BodyTube2",
            "length":        73.0,
            "radius_outer":  12.5,
            "wall":          3.5,
            "mat":           "body2",
        },
    ],
    "transitions": [
        {
            "name":              "Transition",
            "length":            50.0,
            "radius_front_outer": 20.0,
            "radius_rear_outer":  12.5,
            "wall":              2.0,
            "mat":               "transition",
        },
    ],
    "fins": {
        "count":      4,
        "root_chord": 25.0,     # 翼根弦长
        "tip_chord":  12.0,     # 翼梢弦长
        "height":     50.0,     # 翼展
        "sweep":      40.0,     # 后掠距离
        "thickness":  1.0,      # 厚度
        "mat":        "fins",
    },
    "materials": {
        "nose":       (0.85, 0.35, 0.10),
        "body":       (0.92, 0.92, 0.92),
        "body2":      (0.80, 0.80, 0.80),
        "transition": (0.25, 0.50, 0.85),
        "fins":       (0.12, 0.12, 0.18),
    },
}


# ================================================================
# 底层几何工具
# ================================================================

def ring(bm, radius, z, seg=None):
    """创建一圈顶点，圆心 (0, 0, z)，半径 radius。

    Args:
        bm: bmesh 对象
        radius: 半径 (mm)
        z: Z 坐标 (mm)
        seg: 顶点数，默认使用全局 SEGMENTS
    Returns:
        [bmesh.types.BMVert] 顶点列表
    """
    if seg is None:
        seg = DEFAULT_PARAMS["segments"]
    verts = []
    for i in range(seg):
        a = 2.0 * math.pi * i / seg
        verts.append(bm.verts.new((radius * math.cos(a),
                                   radius * math.sin(a),
                                   z)))
    return verts


def quad_ring(bm, ring_a, ring_b):
    """连接两圈顶点形成四边形带（外法线朝外）。

    用法: 外面 (外顶圈→外底圈)
    """
    n = len(ring_a)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((ring_a[i], ring_a[j], ring_b[j], ring_b[i]))


def quad_ring_inner(bm, ring_a, ring_b):
    """连接两圈顶点形成四边形带（反绕，外法线朝内）。

    用法: 内面 (内顶圈→内底圈)
    """
    n = len(ring_a)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((ring_a[i], ring_b[i], ring_b[j], ring_a[j]))


def cap_ring(bm, outer, inner, flip=False):
    """环形端面: outer→inner 之间填充四边形。

    Args:
        flip: True 时反绕 (底端面)
    """
    n = len(outer)
    for i in range(n):
        j = (i + 1) % n
        if flip:
            bm.faces.new((outer[j], outer[i], inner[i], inner[j]))
        else:
            bm.faces.new((outer[i], outer[j], inner[j], inner[i]))


def build_shell(bm, to, bo, ti, bi):
    """四圈顶点 → 封闭薄壁管/锥（外/内/顶环/底环）。

    每条边恰好被 2 个面共享 → 数学保证流形。
    """
    quad_ring(bm, to, bo)           # 外面
    quad_ring_inner(bm, ti, bi)     # 内面
    cap_ring(bm, to, ti)            # 顶环
    cap_ring(bm, bo, bi, flip=True) # 底环


# ================================================================
# 零件构建函数
# ================================================================

def make_ellipsoid_nose(bm, params, z_top=0.0, slices=None):
    """构造椭圆体头锥（多切片法，尖端小圆盘封顶）。

    半椭圆公式: r(z) = R * sqrt(1 - ((z-L)/L)²)
    其中 L = 头锥长度, R = 底座半径

    Args:
        bm:       bmesh
        params:   nose 参数字典
        z_top:    头锥尖端 Z (默认 0)
        slices:   纵向切片数 (默认使用全局设置)
    Returns:
        (z_bottom, n_vertices) 底座 Z 坐标和总顶点数
    """
    L    = params["length"]
    R_o  = params["base_radius_outer"]
    wall = params["wall"]
    R_i  = R_o - wall
    z_bot = z_top + L

    if slices is None:
        slices = DEFAULT_PARAMS["ellipse_slices"]
    seg = DEFAULT_PARAMS["segments"]

    ro_all = []  # 外圈 per slice
    ri_all = []  # 内圈 per slice

    for i in range(slices + 1):
        z = z_top + L * i / slices
        t = (z - z_bot) / L  # ∈ [-1, 0]
        r_o = max(params["tip_radius_outer"],
                  R_o * math.sqrt(max(0.0, 1.0 - t * t)))
        r_i = max(params["tip_radius_inner"],
                  R_i * math.sqrt(max(0.0, 1.0 - t * t)))

        ro_all.append(ring(bm, r_o, z, seg))
        ri_all.append(ring(bm, r_i, z, seg))

    # 连接相邻切片
    for s in range(slices):
        quad_ring(bm, ro_all[s], ro_all[s + 1])
        quad_ring_inner(bm, ri_all[s], ri_all[s + 1])

    # 尖端封顶 (小圆盘)
    cap_ring(bm, ro_all[0], ri_all[0])

    # 底座环形端面
    cap_ring(bm, ro_all[-1], ri_all[-1], flip=True)

    return z_bot, len(bm.verts)


def make_conical_nose(bm, params, z_top=0.0):
    """构造截头圆锥头锥（顶面小圆盘，非尖点）。

    Args:
        bm:       bmesh
        params:   nose 参数字典
        z_top:    顶端 Z 坐标
    Returns:
        (z_bottom, n_vertices)
    """
    L    = params["length"]
    R_o  = params["base_radius_outer"]
    wall = params["wall"]
    R_i  = R_o - wall
    R_to = params.get("tip_radius_outer", 1.0)
    R_ti = params.get("tip_radius_inner", 0.5)
    z_bot = z_top + L

    to = ring(bm, R_to, z_top)
    ti = ring(bm, R_ti, z_top)
    bo = ring(bm, R_o,  z_bot)
    bi = ring(bm, R_i,  z_bot)

    build_shell(bm, to, bo, ti, bi)
    return z_bot, len(bm.verts)


def make_body_tube(bm, z_top, length, r_out, wall):
    """构造等径薄壁圆管。

    Returns:
        (z_bottom, n_vertices)
    """
    r_in   = r_out - wall
    z_bot  = z_top + length

    to = ring(bm, r_out, z_top)
    bo = ring(bm, r_out, z_bot)
    ti = ring(bm, r_in,  z_top)
    bi = ring(bm, r_in,  z_bot)

    build_shell(bm, to, bo, ti, bi)
    return z_bot, len(bm.verts)


def make_transition(bm, z_top, params):
    """构造截头圆锥过渡段（前大后小）。

    Returns:
        (z_bottom, n_vertices)
    """
    L     = params["length"]
    R_fo  = params["radius_front_outer"]
    R_ro  = params["radius_rear_outer"]
    wall  = params["wall"]
    R_fi  = R_fo - wall
    R_ri  = R_ro - wall
    z_bot = z_top + L

    fo = ring(bm, R_fo, z_top)
    ro = ring(bm, R_ro, z_bot)
    fi = ring(bm, R_fi, z_top)
    ri = ring(bm, R_ri, z_bot)

    build_shell(bm, fo, ro, fi, ri)
    return z_bot, len(bm.verts)


def make_fins(bm, params, z_btm, body_r_out):
    """构造梯形稳定翼 (N 片，绕 Z 轴均布)。

    翼根后缘对齐箭体底部 z_btm。

    Returns:
        n_vertices
    """
    N       = params["count"]
    root    = params["root_chord"]
    tip     = params["tip_chord"]
    height  = params["height"]
    sweep   = params["sweep"]
    t2      = params["thickness"] / 2.0

    z_le = z_btm - root  # 翼根前缘

    # 8 个局部坐标 (x=厚度, y=展向, z=轴向)
    local = [
        (-t2, body_r_out,             z_le),              # v0 底-根前缘
        (-t2, body_r_out + height,    z_le + sweep),      # v1 底-梢前缘
        (-t2, body_r_out + height,    z_le + sweep + tip), # v2 底-梢后缘
        (-t2, body_r_out,             z_le + root),        # v3 底-根后缘
        ( t2, body_r_out,             z_le),              # v4 顶-根前缘
        ( t2, body_r_out + height,    z_le + sweep),      # v5 顶-梢前缘
        ( t2, body_r_out + height,    z_le + sweep + tip), # v6 顶-梢后缘
        ( t2, body_r_out,             z_le + root),        # v7 顶-根后缘
    ]

    for fi in range(N):
        angle = 2.0 * math.pi * fi / N
        ca, sa = math.cos(angle), math.sin(angle)

        fv = []
        for lx, ly, lz in local:
            fv.append(bm.verts.new((lx * ca - ly * sa,
                                    lx * sa + ly * ca,
                                    lz)))

        # 6 封闭面 → 流形盒体
        bm.faces.new((fv[0], fv[1], fv[2], fv[3]))   # 底面
        bm.faces.new((fv[4], fv[7], fv[6], fv[5]))   # 顶面 (反绕)
        bm.faces.new((fv[0], fv[4], fv[5], fv[1]))   # 前缘
        bm.faces.new((fv[3], fv[2], fv[6], fv[7]))   # 后缘
        bm.faces.new((fv[0], fv[3], fv[7], fv[4]))   # 翼根
        bm.faces.new((fv[1], fv[5], fv[6], fv[2]))   # 翼梢

    return len(bm.verts)


# ================================================================
# Blender 对象化
# ================================================================

def finalize(name, bm, mat=None, scale=None):
    """bmesh → Blender 对象。内部完成缩放 + 去重 + 法线重算。

    Args:
        name:  对象名称
        bm:    bmesh 对象 (调用后 free)
        mat:   材质
        scale: 缩放因子 (默认使用全局 scale)
    Returns:
        bpy.types.Object
    """
    if scale is None:
        scale = DEFAULT_PARAMS["scale"]

    for v in bm.verts:
        v.co.x *= scale
        v.co.y *= scale
        v.co.z *= scale

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    if mat:
        obj.data.materials.append(mat)

    for p in obj.data.polygons:
        p.use_smooth = True

    return obj


def make_mat(name, rgb):
    """创建 Principled BSDF 材质 (兼容 Blender 中英文界面)。

    Args:
        name: 材质名称
        rgb:  (r, g, b) 浮点三元组
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = None
    for n in mat.node_tree.nodes:
        if 'BSDF' in getattr(n, 'bl_idname', '') or 'BSDF' in getattr(n, 'name', ''):
            bsdf = n
            break
    if bsdf is None:
        for n in mat.node_tree.nodes:
            if hasattr(n, 'inputs') and 'Base Color' in n.inputs:
                bsdf = n
                break
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    return mat


# ================================================================
# 主构建流程
# ================================================================

def build_rocket(params=None):
    """从参数字典构建完整火箭模型。

    Args:
        params: 参数字典，为 None 时使用 DEFAULT_PARAMS

    Returns:
        [obj_nose, obj_tubes, obj_transitions, obj_fins]
        各零件对象列表
    """
    if params is None:
        params = DEFAULT_PARAMS

    prefix  = params.get("prefix", "Rocket")
    scale   = params.get("scale", 0.001)
    seg     = params.get("segments", 48)

    # 更新全局默认 (ring 函数引用)
    DEFAULT_PARAMS["segments"] = seg
    DEFAULT_PARAMS["scale"] = scale

    # --- 清理旧对象 ---
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefix + "_"):
            bpy.data.objects.remove(obj, do_unlink=True)

    # --- 材质 ---
    mats = {}
    for key, rgb in params.get("materials", {}).items():
        mats[key] = make_mat(f"{prefix}_Mat_{key}", rgb)

    nose_mat_key = params["nose"].get("mat", "nose")
    nose_mat     = mats.get(nose_mat_key)

    # ========== 构建 ==========
    print("=" * 60)
    print(f"  {prefix} — OpenRocket → Blender")
    print("=" * 60)

    # 1) 头锥
    z_cur = 0.0
    nc_bm = bmesh.new()
    nose_type = params["nose"].get("type", "ellipsoid")
    if nose_type == "ellipsoid":
        print(f"  [1] 椭圆体头锥...")
        z_cur, _ = make_ellipsoid_nose(nc_bm, params["nose"])
    else:
        print(f"  [1] 截头圆锥头锥...")
        z_cur, _ = make_conical_nose(nc_bm, params["nose"])

    obj_nc = finalize(f"{prefix}_NoseCone", nc_bm, nose_mat)
    print(f"       Z={z_cur:.0f}mm  verts={len(obj_nc.data.vertices)} faces={len(obj_nc.data.polygons)}")

    # 2) 箭体管
    obj_tubes = []
    for i, bt in enumerate(params.get("body_tubes", [])):
        if i == 0:
            # 如果存在级间断，箭体管在级间断之前
            pass

    # 收集所有段并计算 Z 轴位置
    # 顺序: 头锥 → [body_tubes 和 transitions 交替] → fins
    # 根据参数结构，body_tubes 和 transitions 按顺序交叉
    # 但参数结构是 body_tubes 列表 + transitions 列表
    # 这里默认: nose → body_tubes[0] → transitions[0] → body_tubes[1] → fins

    z_positions = [("nose", z_cur)]

    # 交错放置管和锥
    bt_idx = 0
    tr_idx = 0
    bt_list = params.get("body_tubes", [])
    tr_list = params.get("transitions", [])

    # 构建序列: bt[0], tr[0], bt[1], tr[1], ...
    for i in range(max(len(bt_list), len(tr_list) + 1)):  # 管比锥多1
        if bt_idx < len(bt_list):
            bt = bt_list[bt_idx]
            bm = bmesh.new()
            print(f"  [{2+bt_idx*2}] {bt['name']}...")
            z_cur, _ = make_body_tube(bm, z_cur, bt["length"],
                                      bt["radius_outer"], bt["wall"])
            mat_key = bt.get("mat", "body")
            obj = finalize(f"{prefix}_{bt['name']}", bm, mats.get(mat_key))
            obj_tubes.append(obj)
            print(f"       Z={z_cur:.0f}mm  verts={len(obj.data.vertices)} faces={len(obj.data.polygons)}")
            bt_idx += 1

        if tr_idx < len(tr_list):
            tr = tr_list[tr_idx]
            bm = bmesh.new()
            print(f"  [{2+tr_idx*2+1}] {tr['name']}...")
            z_cur, _ = make_transition(bm, z_cur, tr)
            mat_key = tr.get("mat", "transition")
            obj = finalize(f"{prefix}_{tr['name']}", bm, mats.get(mat_key))
            obj_tubes.append(obj)
            print(f"       Z={z_cur:.0f}mm  verts={len(obj.data.vertices)} faces={len(obj.data.polygons)}")
            tr_idx += 1

    z_btm = z_cur  # 箭体底部 Z

    # 3) 稳定翼
    obj_fin = None
    if "fins" in params:
        print(f"  [最后] 稳定翼 ×{params['fins']['count']}...")
        fin_bm = bmesh.new()
        last_bt = bt_list[-1] if bt_list else {"radius_outer": 0}
        make_fins(fin_bm, params["fins"], z_btm, last_bt["radius_outer"])
        fin_mat_key = params["fins"].get("mat", "fins")
        obj_fin = finalize(f"{prefix}_Fins", fin_bm, mats.get(fin_mat_key))
        sweep_deg = math.degrees(math.atan(
            params["fins"]["sweep"] / params["fins"]["height"]))
        print(f"       verts={len(obj_fin.data.vertices)} faces={len(obj_fin.data.polygons)}")
        print(f"       后掠角={sweep_deg:.1f}°")

    # ========== 报告 ==========
    print("\n" + "=" * 60)
    print(f"  构建完成 — 箭体总长 {z_btm:.0f}mm ({z_btm/10:.1f}cm)")
    print(f"  所有零件 location=(0,0,0), 顶点已含绝对 Z 坐标")
    print("=" * 60)

    return obj_nc, obj_tubes, obj_fin


# ================================================================
# CLI 入口 (在 Blender 内直接运行此脚本)
# ================================================================
if __name__ == "__main__":
    build_rocket(DEFAULT_PARAMS)
