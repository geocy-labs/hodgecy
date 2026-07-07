"""Graph exports for concurrency-aware arrangement profiles."""

from __future__ import annotations

from .concurrency import ArrangementConcurrencyProfile


def build_concurrency_graph(profile: ArrangementConcurrencyProfile):
    """Build the typed concurrency graph for an arrangement profile."""
    try:
        import networkx as nx
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("networkx is required to build concurrency graphs.") from exc

    graph = nx.Graph()
    for plane_number in range(1, profile.plane_count + 1):
        graph.add_node(f"plane:p{plane_number}", type="plane")
    for line in profile.double_lines:
        graph.add_node(f"double_line:{line.line_id}", type="double_line")
        for plane_label in line.planes:
            graph.add_edge(f"plane:{plane_label}", f"double_line:{line.line_id}")
    for point in profile.multiple_points:
        graph.add_node(f"multiple_point:{point.point_id}", type=f"p{point.multiplicity}")
        for line_id in point.incident_double_lines:
            graph.add_edge(f"double_line:{line_id}", f"multiple_point:{point.point_id}")
    return graph


def build_p4_collinearity_graph(profile: ArrangementConcurrencyProfile):
    """Build the p4-collinearity graph for an arrangement profile."""
    try:
        import networkx as nx
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("networkx is required to build p4 collinearity graphs.") from exc

    point_lookup = {point.point_id: point for point in profile.multiple_points}
    graph = nx.Graph()
    for point in profile.multiple_points:
        if point.multiplicity != 4:
            continue
        graph.add_node(
            point.point_id,
            type="p4",
            coordinates=point.coordinates,
            label=point.point_id,
        )
    for line in profile.double_lines:
        p4_points = [point_id for point_id in line.incident_multiple_points if point_lookup[point_id].multiplicity == 4]
        if len(p4_points) < 2:
            continue
        for index, left in enumerate(sorted(p4_points)):
            for right in sorted(p4_points)[index + 1 :]:
                if graph.has_edge(left, right):
                    graph.edges[left, right]["lines"].append(line.line_id)
                else:
                    graph.add_edge(left, right, lines=[line.line_id])
    return graph


def p4_collinearity_certificate_rows(profile: ArrangementConcurrencyProfile) -> list[dict[str, object]]:
    """Return certificate rows for the p4-collinearity graph."""
    graph = build_p4_collinearity_graph(profile)
    rows: list[dict[str, object]] = []
    for node in sorted(graph.nodes):
        coordinates = graph.nodes[node].get("coordinates")
        neighbor_labels = sorted(graph.neighbors(node))
        rows.append(
            {
                "arrangement": profile.arrangement_id,
                "vertex_label": node,
                "coordinates": "(" + ":".join(str(value) for value in coordinates) + ")",
                "degree": graph.degree(node),
                "neighbor_labels": ",".join(neighbor_labels),
            }
        )
    return rows


def colored_graph_isomorphic(profile_a: ArrangementConcurrencyProfile, profile_b: ArrangementConcurrencyProfile):
    """Return typed-graph isomorphism status if networkx is available."""
    try:
        from networkx.algorithms import isomorphism
    except ImportError:  # pragma: no cover
        return None

    graph_a = build_concurrency_graph(profile_a)
    graph_b = build_concurrency_graph(profile_b)
    matcher = isomorphism.GraphMatcher(
        graph_a,
        graph_b,
        node_match=lambda left, right: left.get("type") == right.get("type"),
    )
    return matcher.is_isomorphic()
