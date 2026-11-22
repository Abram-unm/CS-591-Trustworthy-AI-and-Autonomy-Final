import argparse
import csv
from itertools import product
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


COMPARISONS = {"<", "<=", "=", "!=", ">=", ">"}


def _number(value, description):
    if isinstance(value, bool):
        raise ValueError(f"{description} must be a finite number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{description} must be a finite number") from None
    if not number.is_finite():
        raise ValueError(f"{description} must be a finite number")
    return format(number, "f")


def _read_graph(path):
    edges = {}
    nodes = []
    seen_nodes = set()
    with path.open(newline="", encoding="utf-8") as graph_file:
        reader = csv.DictReader(graph_file)
        fieldnames = reader.fieldnames or []
        if not {"source", "dest", "weight"}.issubset(fieldnames):
            raise ValueError("graph CSV must have source,dest,weight columns")
        for line, row in enumerate(reader, start=2):
            source, dest = row["source"], row["dest"]
            if not source or not dest:
                raise ValueError(f"graph CSV line {line} has an empty node ID")
            for node in (source, dest):
                if node not in seen_nodes:
                    nodes.append(node)
                    seen_nodes.add(node)
            weight = _number(row["weight"], f"weight on line {line}")
            if Decimal(weight) < 0:
                raise ValueError(f"weight on line {line} must be nonnegative")
            cap_value = row.get("max_flow_rate")
            max_flow_rate = (
                None
                if cap_value is None or not cap_value.strip()
                else _number(cap_value, f"max_flow_rate on line {line}")
            )
            if max_flow_rate is not None and Decimal(max_flow_rate) < 0:
                raise ValueError(f"max_flow_rate on line {line} must be nonnegative")
            edge = frozenset((source, dest))
            edge_data = (weight, max_flow_rate)
            if edge in edges and edges[edge] != edge_data:
                raise ValueError(
                    f"edge {source}-{dest} has inconsistent attributes in the CSV"
                )
            edges[edge] = edge_data
    if not nodes:
        raise ValueError("graph CSV contains no edges")
    return nodes, edges


def _node_variable(node, node_variables):
    try:
        return node_variables[node]
    except KeyError:
        raise ValueError(f"policy refers to unknown node {node!r}") from None


def _policy_term(term, node_variables):
    if not isinstance(term, dict) or len(term) != 1:
        raise ValueError("guard terms must be {'node': id} or {'constant': number}")
    if "node" in term:
        return _node_variable(str(term["node"]), node_variables)
    if "constant" in term:
        return _number(term["constant"], "guard constant")
    raise ValueError("guard terms must be {'node': id} or {'constant': number}")


def _guard(clauses, node_variables):
    if not isinstance(clauses, list):
        raise ValueError("each mode's 'when' value must be a list of comparisons")
    if not clauses:
        return "true"
    comparisons = []
    for clause in clauses:
        if not isinstance(clause, dict) or set(clause) != {"left", "op", "right"}:
            raise ValueError("each guard comparison needs left, op, and right")
        if not isinstance(clause["op"], str) or clause["op"] not in COMPARISONS:
            raise ValueError(f"unsupported guard comparison {clause['op']!r}")
        left = _policy_term(clause["left"], node_variables)
        right = _policy_term(clause["right"], node_variables)
        comparisons.append(f"({left} {clause['op']} {right})")
    return " & ".join(comparisons)


def _read_config(path, nodes, edges):
    with path.open(encoding="utf-8") as config_file:
        config = json.load(config_file)
    if not isinstance(config, dict):
        raise ValueError("config must be a JSON object")

    required = {
        "initial_levels",
        "max_inflow_rate",
        "outlet_conductances",
        "modes",
    }
    missing = required - config.keys()
    if missing:
        raise ValueError(f"config is missing: {', '.join(sorted(missing))}")

    if "overflow_level" in config and "overflow_levels" in config:
        raise ValueError("specify either overflow_level or overflow_levels, not both")
    if "overflow_levels" in config:
        overflow_config = config["overflow_levels"]
        if not isinstance(overflow_config, dict):
            raise ValueError("overflow_levels must be a JSON object keyed by node ID")
        overflow_levels = {
            str(node): _number(value, f"overflow level for node {node!r}")
            for node, value in overflow_config.items()
        }
        if set(overflow_levels) != set(nodes):
            missing_nodes = sorted(set(nodes) - overflow_levels.keys())
            extra_nodes = sorted(overflow_levels.keys() - set(nodes))
            details = []
            if missing_nodes:
                details.append(f"missing nodes: {', '.join(missing_nodes)}")
            if extra_nodes:
                details.append(f"unknown nodes: {', '.join(extra_nodes)}")
            raise ValueError(
                "overflow_levels must specify every graph node exactly (" +
                "; ".join(details) + ")"
            )
    elif "overflow_level" in config:
        limit = _number(config["overflow_level"], "overflow_level")
        overflow_levels = {node: limit for node in nodes}
    else:
        raise ValueError("config must include overflow_level or overflow_levels")

    max_inflow_rate = _number(config["max_inflow_rate"], "max_inflow_rate")
    if Decimal(max_inflow_rate) < 0:
        raise ValueError("max_inflow_rate must be nonnegative")

    initial = config["initial_levels"]
    if not isinstance(initial, dict):
        raise ValueError("initial_levels must be a JSON object keyed by node ID")
    initial = {str(node): _number(value, f"initial level for node {node!r}")
               for node, value in initial.items()}
    if any(Decimal(value) < 0 for value in initial.values()):
        raise ValueError("initial_levels must be nonnegative")
    if set(initial) != set(nodes):
        missing_nodes = sorted(set(nodes) - initial.keys())
        extra_nodes = sorted(initial.keys() - set(nodes))
        details = []
        if missing_nodes:
            details.append(f"missing nodes: {', '.join(missing_nodes)}")
        if extra_nodes:
            details.append(f"unknown nodes: {', '.join(extra_nodes)}")
        raise ValueError("initial_levels must specify every graph node exactly (" +
                         "; ".join(details) + ")")

    minimum_config = config.get("minimum_levels")
    minimum_levels = None
    if minimum_config is not None:
        if not isinstance(minimum_config, dict):
            raise ValueError("minimum_levels must be a JSON object keyed by node ID")
        minimum_levels = {
            str(node): _number(value, f"minimum level for node {node!r}")
            for node, value in minimum_config.items()
        }
        if set(minimum_levels) != set(nodes):
            missing_nodes = sorted(set(nodes) - minimum_levels.keys())
            extra_nodes = sorted(minimum_levels.keys() - set(nodes))
            details = []
            if missing_nodes:
                details.append(f"missing nodes: {', '.join(missing_nodes)}")
            if extra_nodes:
                details.append(f"unknown nodes: {', '.join(extra_nodes)}")
            raise ValueError(
                "minimum_levels must specify every graph node exactly (" +
                "; ".join(details) + ")"
            )
        for node, minimum in minimum_levels.items():
            if Decimal(minimum) < 0:
                raise ValueError(f"minimum level for node {node!r} must be nonnegative")
            if Decimal(minimum) > Decimal(overflow_levels[node]):
                raise ValueError(
                    f"minimum level for node {node!r} cannot exceed its overflow level"
                )

    outlet_config = config["outlet_conductances"]
    if not isinstance(outlet_config, dict) or not outlet_config:
        raise ValueError("outlet_conductances must configure at least one outlet")
    outlet_conductances = {}
    for node, value in outlet_config.items():
        node = str(node)
        if node not in nodes:
            raise ValueError(f"outlet refers to unknown node {node!r}")
        conductance = _number(value, f"outlet conductance for node {node!r}")
        if Decimal(conductance) <= 0:
            raise ValueError("outlet conductances must be positive")
        outlet_conductances[node] = conductance

    node_variables = {node: f"level_{index}" for index, node in enumerate(nodes)}
    inflow_variables = {node: f"inflow_{index}" for index, node in enumerate(nodes)}
    modes_config = config["modes"]
    if not isinstance(modes_config, list) or not modes_config:
        raise ValueError("modes must be a non-empty list")
    modes = []
    for index, mode in enumerate(modes_config):
        required_mode_fields = {"when", "active_edges", "active_outlets"}
        if not isinstance(mode, dict) or not required_mode_fields.issubset(mode):
            raise ValueError(
                f"mode {index} needs 'when', 'active_edges', and 'active_outlets'"
            )
        guard = _guard(mode["when"], node_variables)
        active_edges = mode["active_edges"]
        if not isinstance(active_edges, list):
            raise ValueError(f"mode {index} active_edges must be a list")
        selected_edges = []
        seen_edges = set()
        for edge in active_edges:
            if not isinstance(edge, list) or len(edge) != 2:
                raise ValueError(f"mode {index} edges must be [source, dest] pairs")
            source, dest = map(str, edge)
            key = frozenset((source, dest))
            if key not in edges:
                raise ValueError(f"mode {index} refers to missing edge {source}-{dest}")
            if key not in seen_edges:
                selected_edges.append(key)
                seen_edges.add(key)
        active_outlets = mode["active_outlets"]
        if not isinstance(active_outlets, list):
            raise ValueError(f"mode {index} active_outlets must be a list")
        selected_outlets = []
        seen_outlets = set()
        for node in active_outlets:
            node = str(node)
            if node not in outlet_conductances:
                raise ValueError(
                    f"mode {index} refers to node {node!r} without an outlet"
                )
            if node not in seen_outlets:
                selected_outlets.append(node)
                seen_outlets.add(node)
        modes.append((guard, selected_edges, selected_outlets))

    return (
        overflow_levels,
        initial,
        minimum_levels,
        max_inflow_rate,
        node_variables,
        inflow_variables,
        outlet_conductances,
        modes,
    )


def _mode_program(
    guard,
    active_edges,
    active_outlets,
    nodes,
    edges,
    node_variables,
    inflow_variables,
    max_inflow_rate,
    outlet_conductances,
):
    fixed_terms = {node: [] for node in nodes}
    outlet_terms = {node: [] for node in nodes}
    capped_edges = []
    for edge in active_edges:
        if len(edge) == 1:
            continue
        source, dest = sorted(edge, key=nodes.index)
        weight, max_flow_rate = edges[edge]
        source_variable = node_variables[source]
        dest_variable = node_variables[dest]
        unsaturated_flow = f"{weight} * ({dest_variable} - {source_variable})"
        if max_flow_rate is None:
            fixed_terms[source].append(unsaturated_flow)
            fixed_terms[dest].append(
                f"{weight} * ({source_variable} - {dest_variable})"
            )
        else:
            capped_edges.append(
                (source, dest, unsaturated_flow, max_flow_rate)
            )

    for node in active_outlets:
        outlet_terms[node].append(
            f"{outlet_conductances[node]} * (0 - {node_variables[node]})"
        )

    inflow_assignments = "\n        ".join(
        f"{inflow_variables[node]} := *;" for node in nodes
    )
    inflow_bounds = " & ".join(
        f"({inflow_variables[node]} >= 0 & "
        f"{inflow_variables[node]} <= {max_inflow_rate})"
        for node in nodes
    )
    regions = []
    for source, dest, raw_flow, cap in capped_edges:
        regions.append((
            (cap, f"({raw_flow} >= {cap})"),
            (raw_flow, f"({raw_flow} >= -{cap} & {raw_flow} <= {cap})"),
            (f"-{cap}", f"({raw_flow} <= -{cap})"),
        ))

    branches = []
    for selected_regions in product(*regions):
        terms = {node: list(node_terms) for node, node_terms in fixed_terms.items()}
        region_constraints = [guard]
        for (source, dest, _, _), (flow, constraint) in zip(
            capped_edges, selected_regions
        ):
            terms[source].append(flow)
            terms[dest].append(f"-({flow})")
            region_constraints.append(constraint)
        derivatives = []
        for node in nodes:
            terms[node].extend(outlet_terms[node])
            terms[node].append(inflow_variables[node])
            expression = " + ".join(terms[node])
            derivatives.append(f"{node_variables[node]}' = {expression}")
        ode = ",\n          ".join(derivatives)
        domain = " & ".join(region_constraints)
        branches.append(
            f"?({guard});\n"
            f"        {inflow_assignments}\n"
            f"        ?({inflow_bounds});\n"
            f"        {{{ode} & ({domain})}}"
        )
    return "\n        ++\n        ".join(branches)


def generate_model(graph_path, config_path, property_name="safety"):
    graph_path = Path(graph_path)
    config_path = Path(config_path)
    nodes, edges = _read_graph(graph_path)
    (
        overflow_levels,
        initial,
        minimum_levels,
        max_inflow_rate,
        node_variables,
        inflow_variables,
        outlet_conductances,
        modes,
    ) = _read_config(config_path, nodes, edges)

    declarations = ", ".join(
        [node_variables[node] for node in nodes]
        + [inflow_variables[node] for node in nodes]
    )
    initial_condition = " & ".join(
        f"{node_variables[node]} = {initial[node]}" for node in nodes
    )
    safety_conditions = []
    for node in nodes:
        if minimum_levels is not None:
            safety_conditions.append(
                f"{node_variables[node]} >= {minimum_levels[node]}"
            )
        safety_conditions.append(
            f"{node_variables[node]} <= {overflow_levels[node]}"
        )
    safety_condition = " & ".join(safety_conditions)
    overflow_condition = " | ".join(
        f"{node_variables[node]} > {overflow_levels[node]}" for node in nodes
    )
    programs = [
        _mode_program(
            guard,
            active_edges,
            active_outlets,
            nodes,
            edges,
            node_variables,
            inflow_variables,
            max_inflow_rate,
            outlet_conductances,
        )
        for guard, active_edges, active_outlets in modes
    ]
    switching_program = "\n      ++\n      ".join(programs)
    loop = f"{{\n      {switching_program}\n    }}*"

    if property_name == "safety":
        theorem = "NoNodeOverflow"
        loop += f" @invariant({safety_condition})"
        modality = f"[{loop}]"
        postcondition = f"({safety_condition})"
    elif property_name == "overflow":
        theorem = "NodeOverflowReachable"
        modality = f"<{loop}>"
        postcondition = f"({overflow_condition})"
    else:
        raise ValueError("property_name must be 'safety' or 'overflow'")

    return (
        f'ArchiveEntry "{theorem}"\n\n'
        "ProgramVariables\n"
        f"  Real {declarations};\n"
        "End.\n\n"
        "Problem\n"
        f"    ({initial_condition})\n"
        "    ->\n"
        f"    {modality}\n"
        f"    ({postcondition})\n"
        "End.\n\n"
        "End.\n"
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate a KeymaeraX model for a switched reservoir graph with "
            "bounded inflows and controlled outlets."
        )
    )
    parser.add_argument("--graph", required=True, type=Path, help="edge CSV path")
    parser.add_argument("--config", required=True, type=Path, help="policy/levels JSON path")
    parser.add_argument(
        "--property",
        choices=("safety", "overflow"),
        default="safety",
        help="prove no overflow, or prove that overflow is reachable",
    )
    parser.add_argument("--output", required=True, type=Path, help="output .kyx path")
    args = parser.parse_args()

    try:
        model = generate_model(args.graph, args.config, args.property)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(model, encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
