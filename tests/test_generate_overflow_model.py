import json
import tempfile
import unittest
from pathlib import Path

from keymaera.generate_overflow_model import generate_model


class GenerateOverflowModelTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.graph = self.root / "graph.csv"
        self.graph.write_text(
            "source,dest,weight\n0,1,0.2\n1,0,0.2\n1,2,0.4\n2,1,0.4\n",
            encoding="utf-8",
        )
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({
            "overflow_level": 1,
            "max_inflow_rate": 0.05,
            "initial_levels": {"0": 0.8, "1": 0.2, "2": 0.1},
            "outlet_conductances": {"0": 0.1, "2": 0.3},
            "modes": [
                {
                    "when": [{"left": {"node": "0"}, "op": ">", "right": {"constant": 0.5}}],
                    "active_edges": [["0", "1"], ["1", "2"]],
                    "active_outlets": ["0"],
                },
                {
                    "when": [],
                    "active_edges": [["1", "2"]],
                    "active_outlets": [],
                },
            ],
        }), encoding="utf-8")

    def test_safety_model_contains_switched_conductivity_dynamics(self):
        model = generate_model(self.graph, self.config)

        self.assertIn('ArchiveEntry "NoNodeOverflow"', model)
        self.assertIn(
            "level_0' = 0.2 * (level_1 - level_0) + "
            "0.1 * (0 - level_0) + inflow_0",
            model,
        )
        self.assertIn(
            "level_1' = 0.2 * (level_0 - level_1) + "
            "0.4 * (level_2 - level_1) + inflow_1",
            model,
        )
        self.assertIn("inflow_0 := *;", model)
        self.assertIn("inflow_2 <= 0.05", model)
        self.assertIn("((level_0 > 0.5))", model)
        self.assertIn("level_0 <= 1 & level_1 <= 1 & level_2 <= 1", model)
        self.assertIn(
            "@invariant(level_0 <= 1 & level_1 <= 1 & level_2 <= 1)",
            model,
        )
        self.assertIn("level_1' = 0.4 * (level_2 - level_1) + inflow_1", model)
        self.assertIn(
            "level_2' = 0.4 * (level_1 - level_2) + inflow_2 & (true)",
            model,
        )

    def test_overflow_property_is_existential_reachability(self):
        model = generate_model(self.graph, self.config, "overflow")

        self.assertIn('ArchiveEntry "NodeOverflowReachable"', model)
        self.assertIn("<{\n", model)
        self.assertIn("level_0 > 1 | level_1 > 1 | level_2 > 1", model)

    def test_per_node_overflow_levels_apply_to_both_properties(self):
        config = json.loads(self.config.read_text(encoding="utf-8"))
        del config["overflow_level"]
        config["overflow_levels"] = {"0": 1.0, "1": 0.9, "2": 0.8}
        config["minimum_levels"] = {"0": 0.1, "1": 0.05, "2": 0.02}
        self.config.write_text(json.dumps(config), encoding="utf-8")

        safety_model = generate_model(self.graph, self.config)
        overflow_model = generate_model(self.graph, self.config, "overflow")

        bounds = (
            "level_0 >= 0.1 & level_0 <= 1.0 & "
            "level_1 >= 0.05 & level_1 <= 0.9 & "
            "level_2 >= 0.02 & level_2 <= 0.8"
        )
        self.assertIn(bounds, safety_model)
        self.assertIn("level_0 > 1.0 | level_1 > 0.9 | level_2 > 0.8", overflow_model)

    def test_optional_edge_flow_cap_saturates_signed_conductivity_flow(self):
        self.graph.write_text(
            "source,dest,weight,max_flow_rate\n"
            "0,1,0.2,0.05\n"
            "1,0,0.2,0.05\n"
            "1,2,0.4,\n"
            "2,1,0.4,\n",
            encoding="utf-8",
        )

        model = generate_model(self.graph, self.config)

        first_mode = model.split("\n      ++\n      ", maxsplit=1)[0]
        branches = first_mode.split("\n        ++\n        ")
        self.assertEqual(len(branches), 3)

        raw_flow = "0.2 * (level_1 - level_0)"
        expected_regions = [
            (
                "0.05",
                "-(0.05)",
                f"({raw_flow} >= 0.05)",
            ),
            (
                raw_flow,
                f"-({raw_flow})",
                f"({raw_flow} >= -0.05 & {raw_flow} <= 0.05)",
            ),
            (
                "-0.05",
                "-(-0.05)",
                f"({raw_flow} <= -0.05)",
            ),
        ]
        for source_flow, dest_flow, region in expected_regions:
            with self.subTest(region=region):
                matching_branches = [
                    branch
                    for branch in branches
                    if (
                        f"level_0' = {source_flow} + "
                        "0.1 * (0 - level_0) + inflow_0"
                    ) in branch
                    and (
                        "level_1' = 0.4 * (level_2 - level_1) + "
                        f"{dest_flow} + inflow_1"
                    ) in branch
                ]
                self.assertEqual(len(matching_branches), 1)
                self.assertIn(region, matching_branches[0])

    def test_rejects_inconsistent_reverse_edge_saturation_caps(self):
        self.graph.write_text(
            "source,dest,weight,max_flow_rate\n"
            "0,1,0.2,0.05\n"
            "1,0,0.2,0.06\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "inconsistent attributes"):
            generate_model(self.graph, self.config)

    def test_zero_saturation_cap_allows_no_internal_edge_flow(self):
        self.graph.write_text(
            "source,dest,weight,max_flow_rate\n"
            "0,1,0.2,0\n"
            "1,0,0.2,0\n"
            "1,2,0.4,\n"
            "2,1,0.4,\n",
            encoding="utf-8",
        )

        model = generate_model(self.graph, self.config)

        self.assertIn("level_0' = 0 + 0.1 * (0 - level_0) + inflow_0", model)
        self.assertIn(
            "level_1' = 0.4 * (level_2 - level_1) + -(0) + inflow_1",
            model,
        )

    def test_rejects_negative_edge_saturation_cap(self):
        self.graph.write_text(
            "source,dest,weight,max_flow_rate\n"
            "0,1,0.2,-0.01\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "max_flow_rate on line 2 must be nonnegative"):
            generate_model(self.graph, self.config)

    def test_rejects_incomplete_per_node_overflow_map(self):
        config = json.loads(self.config.read_text(encoding="utf-8"))
        del config["overflow_level"]
        config["overflow_levels"] = {"0": 1.0, "1": 0.9}
        self.config.write_text(json.dumps(config), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "missing nodes: 2"):
            generate_model(self.graph, self.config)

    def test_rejects_conflicting_shared_and_per_node_overflow_levels(self):
        config = json.loads(self.config.read_text(encoding="utf-8"))
        config["overflow_levels"] = {"0": 1.0, "1": 0.9, "2": 0.8}
        self.config.write_text(json.dumps(config), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "either overflow_level or overflow_levels"):
            generate_model(self.graph, self.config)

    def test_optional_per_node_minimum_is_part_of_safety_invariant(self):
        config = json.loads(self.config.read_text(encoding="utf-8"))
        config["minimum_levels"] = {"0": 0.1, "1": 0.05, "2": 0.02}
        self.config.write_text(json.dumps(config), encoding="utf-8")

        model = generate_model(self.graph, self.config)

        bounds = (
            "level_0 >= 0.1 & level_0 <= 1 & "
            "level_1 >= 0.05 & level_1 <= 1 & "
            "level_2 >= 0.02 & level_2 <= 1"
        )
        self.assertIn(bounds, model)
        self.assertIn(f"@invariant({bounds})", model)

    def test_rejects_incomplete_per_node_minimum_map(self):
        config = json.loads(self.config.read_text(encoding="utf-8"))
        config["minimum_levels"] = {"0": 0.1, "1": 0.05}
        self.config.write_text(json.dumps(config), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "missing nodes: 2"):
            generate_model(self.graph, self.config)

    def test_rejects_minimum_above_its_per_node_overflow_level(self):
        config = json.loads(self.config.read_text(encoding="utf-8"))
        del config["overflow_level"]
        config["overflow_levels"] = {"0": 1.0, "1": 0.9, "2": 0.8}
        config["minimum_levels"] = {"0": 0.1, "1": 0.95, "2": 0.02}
        self.config.write_text(json.dumps(config), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "node '1' cannot exceed its overflow level"):
            generate_model(self.graph, self.config)

    def test_rejects_missing_initial_node(self):
        config = json.loads(self.config.read_text(encoding="utf-8"))
        del config["initial_levels"]["2"]
        self.config.write_text(json.dumps(config), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "missing nodes: 2"):
            generate_model(self.graph, self.config)

    def test_requires_a_positive_configured_outlet(self):
        config = json.loads(self.config.read_text(encoding="utf-8"))
        config["outlet_conductances"] = {}
        self.config.write_text(json.dumps(config), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "at least one outlet"):
            generate_model(self.graph, self.config)


if __name__ == "__main__":
    unittest.main()
