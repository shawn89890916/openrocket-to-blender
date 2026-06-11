# 参数参考手册

## 参数字典完整结构

```python
params = {
    # ===== 全局参数 =====
    "prefix":     "Rocket",  # 对象名前缀 (eg. "Rocket_NoseCone")
    "segments":   48,        # 圆周顶点数 (越大越圆, 建议 32~64)
    "scale":      0.001,     # mm → Blender 单位 (1 Blender unit = 1m)
    "ellipse_slices": 48,    # 椭圆体头锥纵向切片数

    # ===== 头锥 =====
    "nose": {
        "type":              "ellipsoid",  # "ellipsoid" 椭圆体 | "conical" 截头圆锥
        "length":            70.0,         # 长度 mm (Z 轴)
        "base_radius_outer": 20.0,         # 底座外半径 mm
        "wall":              2.0,          # 壁厚 mm
        "tip_radius_outer":  0.5,          # 尖端最小外半径 (避免非流形尖点)
        "tip_radius_inner":  0.2,          # 尖端最小内半径
        "mat":               "nose",       # 材质 key, 对应 materials 字典
    },

    # ===== 箭体管 (可多段) =====
    "body_tubes": [
        {
            "name":         "BodyTube1",   # 对象名后缀
            "length":       170.0,         # 长度 mm
            "radius_outer": 20.0,          # 外半径 mm
            "wall":         2.0,           # 壁厚 mm
            "mat":          "body",        # 材质 key
        },
        # ... 更多箭体管
    ],

    # ===== 级间过渡段 (锥形, 可多段) =====
    "transitions": [
        {
            "name":               "Transition",
            "length":             50.0,         # 长度 mm
            "radius_front_outer": 20.0,         # 前端外半径
            "radius_rear_outer":  12.5,         # 后端外半径
            "wall":               2.0,          # 壁厚 mm
            "mat":                "transition",
        },
        # ... 更多过渡段
    ],

    # ===== 稳定翼 =====
    "fins": {
        "count":      4,          # 数量 (绕 Z 轴均布)
        "root_chord": 25.0,       # 翼根弦长 mm
        "tip_chord":  12.0,       # 翼梢弦长 mm
        "height":     50.0,       # 翼展 (从箭体外壁向外) mm
        "sweep":      40.0,       # 后掠距离 mm
        "thickness":  1.0,        # 厚度 mm
        "mat":        "fins",
    },

    # ===== 材质颜色 =====
    "materials": {
        "nose":       (0.85, 0.35, 0.10),  # RGB (0~1)
        "body":       (0.92, 0.92, 0.92),
        "body2":      (0.80, 0.80, 0.80),
        "transition": (0.25, 0.50, 0.85),
        "fins":       (0.12, 0.12, 0.18),
    },
}
```

## Z 轴布局

零件按 **nose → body_tubes ↔ transitions → fins** 顺序沿 +Z 轴堆叠:

```
Z=0    ─── 头锥尖端 (小圆盘封顶)
Z=L_nc ─── 头锥底座 / 箭体1 顶部
  ...  ─── 各段依次叠加
Z=end ─── 最后一节箭体底部 / 翼根后缘
```

**构建段数规则**: `body_tubes` 比 `transitions` 多 1 个。
例如: `body_tubes=[BT1, BT2]` + `transitions=[TR1]` → BT1 → TR1 → BT2 → fins

## 椭圆体头锥公式

```
r(z) = R × √( 1 - ((z - L) / L)² )

其中: L = 头锥长度, R = 底座半径, z ∈ [0, L]
      z=0 → r→0 (尖端), z=L → r=R (底座)
```

内部 48 层切片连接，尖端用 min_radius 封顶圆盘避免非流形。

## 流形 (Watertight) 保证

每个零件使用以下策略保证可 3D 打印:

| 零件     | 策略                                        |
|---------|---------------------------------------------|
| 圆管/锥  | `build_shell`: 外+内+顶环+底环, 每条边被 2 面共享 |
| 椭圆体   | 48 层切片: 外面+内面+尖端封顶+底座环面         |
| 稳定翼   | 8 顶点 → 6 封闭面 (底面+顶面+前缘+后缘+翼根+翼梢) |
| 全局     | `remove_doubles` + `recalc_face_normals`     |
