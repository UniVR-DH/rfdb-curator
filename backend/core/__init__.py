"""Core services for the RossijskijFeatrDB backend.

Modules
-------
config            Application settings loaded from environment / .env.
oxigraph_client   HTTP client for the Oxigraph SPARQL triple store.
schema_extractor  Parses schema.ttl and exposes SHACL shape metadata.
shacl_validator   Wraps pyshacl for pre-write SHACL validation.
seeder            Loads vocab.ttl (and optionally data.ttl) at startup.
blank_node_handler Skolemizes blank nodes before validation and storage.
"""
