"""Regression tests executed inside Blender's Python runtime."""

import copy
import sys
import unittest
from pathlib import Path

import bmesh
import bpy


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import rocket_builder


def count_non_manifold_edges(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    count = sum(1 for edge in bm.edges if len(edge.link_faces) != 2)
    bm.free()
    return count


class RocketBuilderTests(unittest.TestCase):
    def tearDown(self):
        for obj in list(bpy.data.objects):
            if obj.name.startswith("TestRocket_"):
                bpy.data.objects.remove(obj, do_unlink=True)
        for material in list(bpy.data.materials):
            if material.name.startswith("TestRocket_"):
                bpy.data.materials.remove(material)

    def params(self):
        params = copy.deepcopy(rocket_builder.DEFAULT_PARAMS)
        params["prefix"] = "TestRocket"
        return params

    def test_default_parts_are_closed_manifold_meshes(self):
        nose, segments, fins = rocket_builder.build_rocket(self.params())
        for obj in [nose, *segments, fins]:
            self.assertEqual(0, count_non_manifold_edges(obj), obj.name)

    def test_ellipse_slices_parameter_is_honored(self):
        params = self.params()
        params["ellipse_slices"] = 8
        nose, _, _ = rocket_builder.build_rocket(params)
        expected_vertices = 2 * (params["ellipse_slices"] + 1) * params["segments"]
        self.assertEqual(expected_vertices, len(nose.data.vertices))

    def test_documented_minimum_nose_parameters_work(self):
        params = self.params()
        params["nose"].pop("tip_radius_outer")
        params["nose"].pop("tip_radius_inner")
        nose, _, _ = rocket_builder.build_rocket(params)
        self.assertGreater(len(nose.data.vertices), 0)

    def test_invalid_wall_is_rejected_before_geometry_creation(self):
        params = self.params()
        params["body_tubes"][0]["wall"] = params["body_tubes"][0]["radius_outer"]
        with self.assertRaisesRegex(ValueError, "wall must be smaller"):
            rocket_builder.build_rocket(params)
        self.assertIsNone(bpy.data.objects.get("TestRocket_NoseCone"))

    def test_rebuild_reuses_materials(self):
        params = self.params()
        rocket_builder.build_rocket(params)
        rocket_builder.build_rocket(params)
        names = [mat.name for mat in bpy.data.materials if mat.name.startswith("TestRocket_Mat_")]
        self.assertEqual(len(params["materials"]), len(names))
        self.assertFalse(any(name.endswith(".001") for name in names))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RocketBuilderTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
