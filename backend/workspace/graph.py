from dataclasses import asdict, dataclass, field
from typing import Any

from tools.duplicates import find_duplicates


VALID_RELATIONSHIP_TYPES = {
    "duplicate",
    "version_of",
    "generated_from",
    "referenced_by",
    "related_to",
}


@dataclass
class Edge:
    source: str
    target: str
    relationship: str
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkspaceGraph:
    """
    Simple undirected-for-symmetric-relationships (duplicate,
    related_to) / directed-for-asymmetric-relationships (version_of,
    generated_from, referenced_by) adjacency graph.
    """

    _SYMMETRIC_RELATIONSHIPS = {"duplicate", "related_to"}

    def __init__(self) -> None:
        self.nodes: set[str] = set()
        self.edges: list[Edge] = []

    def add_node(self, path: str) -> None:
        self.nodes.add(path)

    def add_relationship(
        self,
        source: str,
        target: str,
        relationship: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if relationship not in VALID_RELATIONSHIP_TYPES:
            raise ValueError(
                f"Unknown relationship type: {relationship}. "
                f"Valid types: {sorted(VALID_RELATIONSHIP_TYPES)}"
            )

        self.add_node(source)
        self.add_node(target)

        self.edges.append(
            Edge(
                source=source,
                target=target,
                relationship=relationship,
                metadata=metadata or {},
            )
        )

    def neighbors(self, path: str, relationship: str | None = None) -> list[str]:
        """
        Return every node connected to `path`, optionally filtered to a
        single relationship type. Symmetric relationships are matched
        in either direction; asymmetric ones only outward from `path`
        (use `incoming()` for the reverse direction).
        """

        results = []

        for edge in self.edges:
            if relationship and edge.relationship != relationship:
                continue

            if edge.source == path:
                results.append(edge.target)
            elif (
                edge.relationship in self._SYMMETRIC_RELATIONSHIPS
                and edge.target == path
            ):
                results.append(edge.source)

        return results

    def incoming(self, path: str, relationship: str | None = None) -> list[str]:
        return [
            edge.source
            for edge in self.edges
            if edge.target == path
            and (relationship is None or edge.relationship == relationship)
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": sorted(self.nodes),
            "edges": [asdict(edge) for edge in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkspaceGraph":
        graph = cls()

        for node in data.get("nodes", []):
            graph.add_node(node)

        for edge_data in data.get("edges", []):
            graph.add_relationship(
                source=edge_data["source"],
                target=edge_data["target"],
                relationship=edge_data["relationship"],
                metadata=edge_data.get("metadata", {}),
            )

        return graph


def build_graph_from_files(files: list[dict]) -> WorkspaceGraph:
    """
    Build a WorkspaceGraph from a list of scanned file dicts (the same
    shape tools.scanner.scan_directory / engines.context.build_storage_context
    produce), automatically wiring up `duplicate` edges between files
    with identical content hashes.
    """

    graph = WorkspaceGraph()

    for file_info in files:
        graph.add_node(file_info["path"])

    duplicate_groups = find_duplicates(files)

    for group in duplicate_groups:
        paths = [file_info["path"] for file_info in group]

        # Connect every pair in the group as `duplicate` (small groups
        # in practice - file trees rarely have dozens of byte-identical
        # copies - so the O(n^2) pairing is not a concern here).
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                graph.add_relationship(
                    paths[i],
                    paths[j],
                    "duplicate",
                )

    return graph