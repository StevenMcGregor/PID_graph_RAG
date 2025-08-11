## DEXPI P&ID to Neo4j Knowledge Graph

Command-line workflow to parse a DEXPI XML, produce a NetworkX graph, export GraphML, and optionally load to Neo4j.

### Setup

1. Create/activate your virtualenv (you have `venv/` already):
   - Windows PowerShell: `venv\Scripts\Activate.ps1`
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment template and set values:
   - Windows PowerShell: `Copy-Item _env.example .env`

### Usage

Parse XML and export GraphML:
```bash
python main.py C01V04-VER.EX01.xml --graphml pid.graphml
```

Load into Neo4j (requires env vars or CLI flags):
```bash
python main.py C01V04-VER.EX01.xml --load-neo4j \
  --neo4j-uri bolt://localhost:7687 \
  --neo4j-user neo4j \
  --neo4j-password password
```

Or set environment variables:
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### Sample Queries

See `sample_queries.cypher` for examples.

### Notes

- The loader tries multiple pyDEXPI APIs (`DexpiLoader`, `ProteusSerializer`) for compatibility across versions.
- Nodes get label `Component` and `id` property; relationships get type `CONNECTED_TO` with all available attributes.
- Create an index (done automatically): `CREATE INDEX component_id IF NOT EXISTS FOR (n:Component) ON (n.id)`.

