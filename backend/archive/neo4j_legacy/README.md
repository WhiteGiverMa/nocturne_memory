# Neo4j Legacy Archive

This directory contains the sealed pre-1.0 Neo4j migration implementation.

It is **not** part of the active Nocturne Memory runtime. Active backend code must not import from this directory. The files are preserved only for users who still need to manually migrate an old Neo4j-backed installation into the current SQLite/PostgreSQL graph model.

Manual migration entry point from the `backend/` directory:

```bash
python archive/neo4j_legacy/migrate_neo4j_to_sqlite.py
```

The Neo4j Python driver is intentionally not included in `backend/requirements.txt`; install it manually only when running this archived script:

```bash
pip install "neo4j>=5.16.0"
```
