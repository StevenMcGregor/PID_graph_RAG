# Simpfrom AI_ulities import generate_pnid_response, start_pnid_chate DEXPI to Neo4j converter
import os
from dotenv import load_dotenv  # <-- Das war das fehlende Import!

from PnID_utilities import load_dexpi_model, to_networkx_graph, export_graphml
from neo4j_utilities import load_graph_to_neo4j
from AI_ulities import generate_pnid_response,start_pnid_chat

# Load environment variables from .env file
load_dotenv()

def main_test_neo4j() -> int:
    """Test Neo4j loading with fixed XML file"""
    dexpi_xml = "C01V04-VER.EX01.xml"
    
    # Check XML file exists
    if not os.path.isfile(dexpi_xml):
        print(f"ERROR: File not found: {dexpi_xml}")
        return 1

    try:
        # Parse XML and create graph
        print("Parsing XML...")
        model = load_dexpi_model(dexpi_xml)
        
        print("Creating graph...")
        graph = to_networkx_graph(model)
        
        # Export GraphML (optional)
        graphml_file = "pid_neo4j_test.graphml"
        print(f"Exporting to {graphml_file}...")
        export_graphml(graph, graphml_file)
        print("GraphML exported")
        
        # Load to Neo4j with default/env values
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER") 
        password = os.getenv("NEO4J_PASSWORD")

        print(f" Neo4j DATA ACCESS: {uri}, User: {user}, Password: {password}")
        
        print("Loading to Neo4j...")
        load_graph_to_neo4j(graph, uri, user, password)
        print("Neo4j loading complete!")
        
        print("✅ Neo4j test completed successfully!")
        return 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def main_test_chat() -> int:
    """Start P&ID chat system with graph context"""
    dexpi_xml = "C01V04-VER.EX01.xml"

    # Check XML file exists
    if not os.path.isfile(dexpi_xml):
        print(f"ERROR: File not found: {dexpi_xml}")
        return 1
    
    try:
        # Parse XML and create graph
        print("Parsing XML...")
        model = load_dexpi_model(dexpi_xml)
        print("Creating graph...")
        graph = to_networkx_graph(model)        
        # Start chat with graph context
        start_pnid_chat(graph)
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def main_test_OpenAI() -> int:
    dexpi_xml = "C01V04-VER.EX01.xml"

    # Check XML file exists
    if not os.path.isfile(dexpi_xml):
        print(f"ERROR: File not found: {dexpi_xml}")
        return 1
    
    # Parse XML and create graph
    print("Parsing XML...")
    model = load_dexpi_model(dexpi_xml)
    print("Creating graph...")
    graph = to_networkx_graph(model)

    # Define prompt
    question = input(f"Enter your question about the P&ID ({dexpi_xml}): ")
    base_prompt = "You are an expert in P&ID representation, and you can help users understand and create P&ID diagrams."
    question = question + str(graph.__dict__) 

    # Generate response using OpenAI
    print("Generating AI response...")
    response = generate_pnid_response(question, base_prompt)
    if response:
        print("AI Response:")
        print(response)
        return 0
    else:
        print("Failed to generate response")
        return 1
        
        
if __name__ == "__main__":
    input_mode = input(f"Choose what to test->C01V04-VER.EX01.xml (1: Neo4j, 2: AI Chat, 3: OpenAI): ").strip()
    if input_mode == "1":
        raise SystemExit(main_test_neo4j())
    elif input_mode == "2":
        raise SystemExit(main_test_chat())
    elif input_mode == "3":
        raise SystemExit(main_test_OpenAI())

