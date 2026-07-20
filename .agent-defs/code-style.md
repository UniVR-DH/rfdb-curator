# Code Style

## Python

### Import Order

```python
import json
from pathlib import Path

from rdflib import Graph

from core.schema_extractor import SchemaExtractor
```

Use standard library -> third-party -> local package.

### Function Docstrings

Use concise docstrings that describe purpose and expected behavior. Add details only when they improve clarity for non-trivial logic.

## Turtle (RDF / SHACL)

### Prefix Declaration

Declare all used prefixes at the top of each `.ttl` file.

### Ontology Preference

Prefer terms already used by the active schema and model, especially LRMoo, CIDOC CRM, and Polifonia ontologies.
Introduce new predicates/classes only when existing vocabularies do not cover the requirement.

### SHACL Rules

- Use `sh:NodeShape` for record-level constraints.
- Keep `sh:class` on property shapes where required by SHACL grammar.
- Use explicit cardinalities with `sh:minCount` and `sh:maxCount`.

## Naming Rules

| Artifact | Convention | Example |
|----------|-----------|---------|
| Python modules | `snake_case.py` | `validation_merge.py` |
| Python classes | `PascalCase` | `ShaclValidator` |
| Python functions / variables | `snake_case` | `merge_related_entities` |
| RDF data resources | `rfdb:PascalCase` | `rfdb:SanPietroburgo` |
| SHACL shapes | `rfdbs:` + suffix `Shape` | `rfdbs:SourceShape` |
| Git branches | `feature/<short-description>` | `feature/add-shape-filter` |
