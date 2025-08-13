# Simple Neo4j utilities
from neo4j import GraphDatabase


def load_graph_to_neo4j(graph, uri: str, user: str, password: str) -> dict:
    """Load NetworkX graph into Neo4j"""
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        # Create index
        session.run("CREATE INDEX component_id IF NOT EXISTS FOR (n:Component) ON (n.id)")
        
        # Load nodes
        for node_id, data in graph.nodes(data=True):
            props = {k: str(v) if v is not None else "" for k, v in data.items()}
            props["id"] = str(node_id)
            session.run(
                "MERGE (n:Component {id: $id}) SET n += $props", 
                id=str(node_id), props=props
            )
        
        # Load edges
        for src, tgt, data in graph.edges(data=True):
            props = {k: str(v) if v is not None else "" for k, v in data.items()}
            session.run(
                "MATCH (a:Component {id: $src}), (b:Component {id: $tgt}) "
                "MERGE (a)-[r:CONNECTED_TO]->(b) SET r += $props",
                src=str(src), tgt=str(tgt), props=props
            )
    
    driver.close()
    return {"nodes_loaded": graph.number_of_nodes(), "edges_loaded": graph.number_of_edges()}
