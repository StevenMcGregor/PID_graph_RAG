// Counts
MATCH (n:Component) RETURN count(n) AS nodeCount;
MATCH ()-[r:CONNECTED_TO]->() RETURN count(r) AS relCount;

// Node property keys frequency
MATCH (n:Component)
UNWIND keys(n) AS k
RETURN k, count(*) AS freq
ORDER BY freq DESC, k ASC
LIMIT 50;

// Candidate type fields distribution
MATCH (n:Component)
WITH n, coalesce(n.type, n.DexpiClass, n.class, n.class_name, n.category, n.component_type) AS t
RETURN t, count(*) AS freq
ORDER BY freq DESC
LIMIT 25;

// Sample nodes (id and a subset of likely fields)
MATCH (n:Component)
RETURN n.id AS id, n.name AS name, n.tag AS tag, n.type AS type, n.DexpiClass AS DexpiClass, n.class AS class, n.line AS line
LIMIT 10;

// Relationship property keys frequency
MATCH ()-[r:CONNECTED_TO]->()
UNWIND keys(r) AS k
RETURN k, count(*) AS freq
ORDER BY freq DESC, k ASC
LIMIT 50;

// Sample relationships
MATCH (a:Component)-[r:CONNECTED_TO]->(b:Component)
RETURN a.id AS source, type(r) AS relType, keys(r) AS relKeys, b.id AS target, r
LIMIT 10;

