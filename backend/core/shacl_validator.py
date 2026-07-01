"""SHACL validation wrapper used by all write routes.

The validator is initialised once at startup with the project schema
(`schema/schema.ttl`) and reused for every POST /data and POST /validate
request.  No data ever reaches Oxigraph without passing through here first.

Important: when validating a newly created entity that references existing
store entities (e.g., a HoldingOrganization referencing a Place), the caller
is responsible for merging the referenced triples into the graph passed to
`validate()`.  See `api/data.py` for the merge strategy.
"""

from __future__ import annotations

from rdflib import Graph, URIRef
from rdflib.namespace import SH
from pyshacl import validate


class ShaclValidator:
    """Wrapper around pyshacl for SHACL validation of RDF graphs.

    Lifecycle: one instance is created at startup (in `app.py`) and stored on
    `app.state.shacl_validator`.  The underlying SHACL graph is parsed once
    from disk and kept in memory for the lifetime of the process.
    """

    def __init__(self, schema_path: str) -> None:
        self._shacl_graph = Graph()
        self._shacl_graph.parse(schema_path, format="turtle")

    def validate(
        self, data_graph: Graph, focus_nodes: list[URIRef] | None = None
    ) -> dict:
        """Validate `data_graph` against the SHACL schema.

        Args:
            data_graph: The rdflib Graph to validate, which should contain both
                the entity being saved and any referenced entities that need to
                satisfy `sh:class` or `sh:node` constraints.
            focus_nodes: Optional list of URIRef nodes to validate. When set,
                the validator applies sh:targetClass matching only to these nodes;
                referenced existing-store nodes present in data_graph are used
                as read-only witnesses for constraint checking but are not
                themselves validated. When None, pyshacl selects focus nodes via
                sh:targetClass / sh:targetNode as usual.

        Returns:
            A dict with keys:
              - ``conforms`` (bool): True when no violations were found.
              - ``violations`` (list[dict]): Parsed `sh:ValidationResult` nodes;
                empty when conforms is True.
        """
        conforms, report_graph, _ = validate(
            data_graph,
            shacl_graph=self._shacl_graph,
            inference="rdfs",
            abort_on_first=False,
            allow_infos=True,
            focus_nodes=focus_nodes,
            js=False,
        )
        return {
            "conforms": bool(conforms),
            "violations": self._parse_report(report_graph),
        }

    @staticmethod
    def _parse_report(report_graph: Graph) -> list[dict]:
        """Extract `sh:Violation` results from a pyshacl report graph.

        Returns one dict per violation with keys `message`, `path`,
        `focusNode`, and `severity`.  Infos and warnings (non-Violation
        severity) are intentionally skipped; pyshacl is called with
        `allow_infos=True` so they appear in the report but are not surfaced
        to the caller.
        """
        violations = []
        for result in report_graph.subjects(SH.resultSeverity, SH.Violation):
            msg = report_graph.value(result, SH.resultMessage)
            path = report_graph.value(result, SH.resultPath)
            focus = report_graph.value(result, SH.focusNode)
            violations.append(
                {
                    "message": str(msg) if msg else "Constraint violation",
                    "path": str(path) if path else None,
                    "focusNode": str(focus) if focus else None,
                    "severity": "sh:Violation",
                }
            )
        return violations
