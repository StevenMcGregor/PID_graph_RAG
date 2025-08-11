// Optional: normalize properties so simpler queries work
// Map node dexpi_class -> type if missing; map rel fluidCode -> medium
MATCH (n:Component)
WHERE n.type IS NULL AND n.dexpi_class IS NOT NULL
SET n.type = n.dexpi_class;

MATCH ()-[r:CONNECTED_TO]->()
WHERE r.medium IS NULL AND r.fluidCode IS NOT NULL
SET r.medium = r.fluidCode;

// 1) Class distribution to discover values
MATCH (n:Component)
RETURN n.dexpi_class AS cls, count(*) AS freq
ORDER BY freq DESC, cls ASC;

// 2) Pumps connected to heat exchangers in line H-500 (using discovered fields)
MATCH path=(p:Component)-[rels:CONNECTED_TO*1..3]->(h:Component)
WHERE toLower(p.dexpi_class) CONTAINS 'pump'
  AND toLower(h.dexpi_class) CONTAINS 'heat'
  AND (
    'H-500' IN [x IN [p.pipingComponentNumber, h.pipingComponentNumber] WHERE x IS NOT NULL]
    OR ANY(r IN rels WHERE r.segmentNumber = 'H-500')
  )
RETURN DISTINCT p.id AS pumpId, h.id AS heatExchangerId;

// 3) Control valves downstream of any compressor
MATCH (c:Component)-[:CONNECTED_TO*1..10]->(v:Component)
WHERE toLower(c.dexpi_class) CONTAINS 'compressor'
  AND (
    toLower(v.dexpi_class) CONTAINS 'valve'
    OR toLower(coalesce(v.deviceTypeName, '')) CONTAINS 'control'
  )
RETURN DISTINCT v.id AS controlValveId
ORDER BY controlValveId;

// 4) Equipment connected by pipes carrying steam (fluidCode ~ 'steam')
MATCH (a:Component)-[r:CONNECTED_TO]->(b:Component)
WHERE toLower(coalesce(r.medium, r.fluidCode, '')) CONTAINS 'steam'
RETURN DISTINCT a.id AS source, b.id AS target, r AS rel;

