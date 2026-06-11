---
name: openrocket-to-blender
description: "Convert OpenRocket rocket design parameters into watertight Blender 3D-printable models. This skill should be used when the user provides rocket geometry specs (nose cone, body tubes, transitions, fins) and wants a Blender Python script to generate STL-slicable parts. Triggers: OpenRocket to Blender, rocket model, 3D print rocket, rocket blender script, or detailed rocket segment dimensions in millimeters."
agent_created: true
---

# OpenRocket → Blender 火箭建模

将 OpenRocket 设计的火箭参数一键转化为 Blender 3D 打印模型。

## 核心能力

- **椭圆体 / 截头圆锥**头锥，多切片法保证流形
- **薄壁圆管**箭体，内外面 + 环形端面封闭
- **锥形级间断**过渡段，匹配前后管径
- **梯形稳定翼** (N 片均布)，后掠角可配
- 所有零件**数学保证 watertight** — 每条边被恰好 2 个面共享
- 代码**纯 bpy + bmesh**，无外部依赖，直接粘贴 Blender 控制台运行

## 何时使用

- 用户给出火箭尺寸参数 (头锥/箭体/级间断/尾翼)
- 用户说要"把 OpenRocket 数据转成 Blender 模型"
- 用户需要可 3D 打印的火箭零件 STL
- 用户提到"写 Blender 脚本" + 火箭几何参数

## 工作流程

### 1. 收集参数

从用户描述中提取参数字典 (单位一律 mm)。完整参数结构见 `references/parameters.md`。

最小必需参数:
- 头锥: type (ellipsoid/conical), length, base_radius_outer, wall
- body_tubes: list[{length, radius_outer, wall}]
- transitions: list[{length, radius_front_outer, radius_rear_outer, wall}] (可选)
- fins: {count, root_chord, tip_chord, height, sweep, thickness}

### 2. 生成脚本

根据参数生成完整的 Blender 控制台脚本。**不要直接修改 `scripts/rocket_builder.py`**，而是为用户生成一份**独立的 `.py` 文件**，包含以下所有要件:

必须包含的内容:
1. **硬编码的参数** (注释标注来源)
2. **`ring()`, `quad_ring()`, `quad_ring_inner()`, `cap_ring()`, `build_shell()`** — 五组核心几何函数
3. **零件构建函数**: 椭圆体头锥 (多切片法), 管, 锥过渡, 羽翼
4. **`finalize()`** — bmesh → Blender 对象 (含 SCALE 缩放 + remove_doubles + recalc_normals)
5. **`make_mat()`** — Principled BSDF 材质 (按 `bl_idname` 类型查找，兼容中英文界面)
6. **Z 轴定位 + 参数核验打印**

生成后必须执行:
- `python -m py_compile` 语法检查
- 逐项核验: 每个外径/内径/壁厚/长度 与用户输入是否一致
- 验证翼根后缘对齐箭体底部

### 3. 关键约束 (必须遵守)

- **不使用 Blender 原生 cone/cylinder** — 全部 bmesh 从零构建，避免非流形
- **头锥不做尖点** — 椭圆体尖端 min radius ≥ 0.5mm (小圆盘封顶)
- **`obj.location` 全设 (0,0,0)** — vertex 已含绝对 Z，无需偏移
- **SCALE 在 `finalize()` 内部乘到每个 vertex** — 不用 `bpy.ops.transform_apply`
- **每条边恰好被 2 个面共享** — 这是流形的充要条件

### 4. Blender 避坑 (见 `scripts/rocket_builder.py`)

已内置在代码中:
- `ShaderNodeMaterialOutput` → 用 `bl_idname` 查找 BSDF 节点
- `apply_scale` bpy.ops → 直接改 vertex.co
- 材质 nodes 访问 → 兼容中英版 node name 差异

## 椭圆体头锥多切片法

半椭圆公式: `r(z) = R × sqrt(1 - ((z-L)/L)^2)`，其中 L=头锥长, R=底座半径。

实现: 沿 Z 轴取 N 个切片，每个切片生成外圈 + 内圈顶点，相邻切片用四边形带连接，尖端用 `cap_ring` 封顶。`references/parameters.md` 含完整数学推导。

## 脚本结构模板

生成的脚本按以下结构组织:
1. 文件头注释 (参数来源 + Z 轴布局)
2. 全局参数 (硬编码)
3. 五组核心几何函数
4. 零件构建函数
5. `finalize()` + `make_mat()`
6. 材质创建
7. 主流程: 构建 → finalize → 定位 → 报告

## 参考

- `references/parameters.md` — 完整参数字典结构和 Z 轴布局说明
- `scripts/rocket_builder.py` — 核心构建器模块 (可 copy 片段，不直接引用)
