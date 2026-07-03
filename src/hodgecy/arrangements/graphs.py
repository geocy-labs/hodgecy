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
