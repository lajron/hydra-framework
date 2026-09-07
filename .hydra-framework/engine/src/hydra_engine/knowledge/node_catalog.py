"""Read-only Knowledge v3 node-catalog facade for outer-layer consumers.

Keeping these high-use discovery operations behind one small boundary prevents
the full schema/validation module from becoming shared vocabulary.
"""

from hydra_engine.knowledge.nodes import (
    discover_knowledge_nodes,
    discover_node_unit_paths,
    knowledge_node_for_path,
    knowledge_root,
    node_root,
    resolve_inheritance,
)

__all__ = (
    "discover_knowledge_nodes",
    "discover_node_unit_paths",
    "knowledge_node_for_path",
    "knowledge_root",
    "node_root",
    "resolve_inheritance",
)
