"""Blank-node handling utilities for the data-entry pipeline.

JSON-LD forms may produce blank nodes in two situations:
  1. The top-level entity has no `@id` (the user did not specify one).
  2. Nested helper-bridge nodes (e.g., AgentRole) are added inline with
     a temporary ``_:temp`` identifier.

Both cases are resolved before SHACL validation so the validator always
sees stable IRIs, and the same IRIs are written to Oxigraph.
"""

from __future__ import annotations

from rfdb_core.vocab import RFDB_BASE


def skolemize(data: dict, parent_id: str) -> dict:
    """Recursively replace blank-node `@id` values with stable skolem IRIs.

    Only list-valued properties are recursed into; scalar values and JSON-LD
    keywords (keys starting with ``@``) are left untouched.

    Strategy: ``<RFDB_BASE><parent_local>_<property_local>_<index>``

    Example::

        parent_id = "https://rosfeatr.eu/rdf/data/L111"
        property  = "core:hasAgentRole"
        index     = 0
        result    = "https://rosfeatr.eu/rdf/data/L111_hasAgentRole_0"
    """
    result = dict(data)
    local_parent = parent_id.replace(RFDB_BASE, "").replace("rfdb:", "")

    for key, value in result.items():
        if key.startswith("@"):
            continue
        if not isinstance(value, list):
            continue

        prop_local = key.split(":")[-1]
        new_list = []
        for i, item in enumerate(value):
            if isinstance(item, dict):
                item = dict(item)
                if item.get("@id", "").startswith("_:"):
                    item["@id"] = f"{RFDB_BASE}{local_parent}_{prop_local}_{i}"
                # Recurse for nested structures
                item = skolemize(item, item.get("@id", parent_id))
            new_list.append(item)
        result[key] = new_list

    return result


def assign_entity_id(data: dict, shape_id: str) -> dict:
    """Assign a generated IRI when `@id` is absent or a blank-node stub.

    The IRI is derived from the shape name plus a random 8-hex-character
    suffix to keep it short and collision-resistant::

        shape_id  = "https://rosfeatr.eu/rdf/schema/PlaceShape"
        result    = "https://rosfeatr.eu/rdf/data/Place_4f3a9d12"

    If the entity already carries a non-blank `@id` it is returned unchanged.
    """
    if data.get("@id") and not data["@id"].startswith("_:"):
        return data
    import uuid

    short = shape_id.split("#")[-1].split("/")[-1].replace("Shape", "")
    result = dict(data)
    result["@id"] = f"{RFDB_BASE}{short}_{uuid.uuid4().hex[:8]}"
    return result
