# Code Style

## Python

### Import Order

```python
import sys
from pathlib import Path
from rdflib import Graph, Namespace, Literal
from rfdbtools.validator import validate_shacl
```

Standard library → third-party → local package.

### Function Docstring Pattern

```python
def validate_shacl(schema_path: str, data_path: str):
    """Validate RDF data against SHACL schema.

    Args:
        schema_path: Path to schema.ttl
        data_path: Path to data.ttl

    Returns:
        sh:ValidationReport (rdflib.Graph)

    Example:
        >>> report = validate_shacl('schema/schema.ttl', 'data/data.ttl')
        >>> assert report.conforms
    """
```

One concise sentence for simple functions; detailed Args/Returns/Example for complex ones.

## Turtle (RDF / SHACL)

### Ontology Preference Order

When modeling RDF data, prefer definitions from ontologies in this order:

1. **FRBR** (`frbr:`) — Foundational bibliographic model
2. **FaBiO** (`fabio:`) — FRBR-aligned bibliographic ontology
3. **Source** (`source:`) — Polifonia source ontology
4. **Core** (`core:`) — Polifonia core ontology

Check `.ontologies/*.ttl` files for property and class definitions before creating custom predicates.

### Prefix Declaration (Required at Top)

```turtle
@prefix core:    <https://w3id.org/polifonia/ontology/core/> .
@prefix fabio:   <http://purl.org/spar/fabio/> .
@prefix frbr:    <http://purl.org/vocab/frbr/core#> .
@prefix mm:      <https://w3id.org/polifonia/ontology/music-meta/> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rfdb:    <https://rfdb.it/data/> .
@prefix sh:      <http://www.w3.org/ns/shacl#> .
@prefix source:  <https://w3id.org/polifonia/ontology/source/> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
```

Stable order matched to `schema/schema.ttl`.

### SHACL Shape Pattern

```turtle
rfdb:SourceShape
  a sh:NodeShape ;
  sh:targetClass source:Source ;
  sh:property [
    sh:path rdfs:label ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:datatype rdf:langString ;
    sh:description "A source must have exactly one label" ;
  ] .
```

### RDF Instance Pattern

```turtle
rfdb:L11a_print
  a fabio:Manifestation, source:Source ;
  rdfs:label "Libretto (1736, San Pietroburgo) printed edition"@en ;
  prism:publicationDate "1736"^^xsd:gYear ;
  dcterms:language "it", "de" ;
  core:hasPlace rfdb:SanPietroburgo ;
  fabio:isPortrayalOf rfdb:T2 ;
  rdfs:seeAlso <https://primo.nlr.ru/permalink/f/df0lai/07NLR_LMS009858715> ;
  rdfs:comment "Rossica 13.8.5.44 (RUS-SPsc)" .
```

### SHACL Design rules

- sh:class is structurally restricted to Property Shapes by the SHACL specification's grammar. Putting it on a Node Shape violates SHACL's structural syntax rules, meaning validators will treat it as an unmapped, non-validating predicate.



## Naming Rules

| Artifact | Convention | Example |
|----------|-----------|---------|
| Python modules | `snake_case.py` | `validate_ontologies.py` |
| Python classes | `PascalCase` | `ShaclValidator` |
| Python functions / variables | `snake_case` | `get_excel` |
| RDF resources | `rfdb:PascalCase` | `rfdb:T2`, `rfdb:PersonShape` |
| SHACL shapes | suffix `Shape` | `rfdb:MusicalWorkShape` |
| Excel sheets (multi-valued) | `<ShapeLabel>__<PropertyName>` | `Source__hasAuthor` |
| Git branches | `feature/<short-description>` | `feature/add-source-shape` |
| Excel export tags | semantic version | `v0.4`, `subset-v1` |
