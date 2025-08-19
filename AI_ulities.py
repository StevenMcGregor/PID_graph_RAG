# Import 
import os
import lxml
from openai import OpenAI
import json
import re
import xml.etree.ElementTree as ET
from lxml import etree as LET


def generate_pnid_response(question, base_prompt):
    """
    Generate P&ID related response using OpenAI GPT
    
    Args:
        question (str): The user's question
        base_prompt (str): The base prompt for P&ID generation
    
    Returns:
        str: AI generated response
    """
    # OpenAI client
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-5",  
            messages=[
                {"role": "system", "content": base_prompt},
                {"role": "user", "content": question}
            ],

        )
        
        ai_result = response.choices[0].message.content
        return ai_result
    
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None
    
    finally:
        # Note: OpenAI client doesn't need explicit closing in newer versions
        pass


def start_pnid_chat(graph):
    """
    Start interactive P&ID chat system with active graph integration
    """
    
    # Welcome message
    print("=" * 80)
    print("🔧 P&ID GRAPH ANALYSIS CHAT SYSTEM")
    print("=" * 80)
    print("📊 Loading P&ID graph data...")
    
    # Chat history for context
    conversation = []
    
    # Convert graph to dictionary and then to string for AI context
    try:
        print("🔄 Converting graph data...")
        # Convert NetworkX graph to dictionary representation
        graph_dict = graph.__dict__
        
        # Convert to string (truncate if too long to avoid token limits)
        graph_str = str(graph_dict)
        print("Graph data size:", len(graph_str), "characters")
        #if len(graph_str) > 100000:  # Limit to avoid token overflow
        #    graph_str = graph_str[:100000] + "... [truncated for brevity]"
        #    print("⚠️  Graph data truncated due to size limitations")
            
        graph_info = f"Complete P&ID Graph Data:\n{graph_str}"
        print(f"✅ Graph loaded successfully! ({graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges)")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not load complete graph data: {e}")
        # Fallback to basic info if conversion fails
        graph_info = f"""
        Graph Information (basic):
        - Nodes: {graph.number_of_nodes()}
        - Edges: {graph.number_of_edges()}
        - Error getting detailed data: {str(e)}
        """
    
    # System prompt with graph context
    system_prompt = f"""You are an expert in P&ID (Piping & Instrumentation Diagrams) analysis. 
    You help analyze process plants and can answer questions about:
    - Components and equipment
    - Process flows  
    - Safety systems
    - Instrumentation
    - Graph structure and relationships
    
    Current P&ID Graph Context:
    {graph_info}
    
    Answer in English and be precise. Use the graph data to provide specific insights."""
    
    # Start chat loop
    print("\n" + "=" * 80)
    print("🚀 CHAT SYSTEM READY!")
    print("=" * 80)
    print(f"💡 Ask questions about the P&ID diagram")
    print("🔍 Available commands: 'exit', 'quit', 'ende', 'stop'")
    print("=" * 80)
    
    while True:
        try:
            user_input = input("\n💬 You: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'ende', 'stop']:
                print("\n" + "=" * 40)
                print("👋 Chat session ended!")
                print("   Thank you for using P&ID Assistant!")
                print("=" * 40)
                break
            
            if not user_input:
                print("⚠️  Please enter a question or command...")
                continue
            
            print("\n" + "─" * 60)
            print("🔍 Processing your question...")
            
            # OpenAI Client
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            # Messages for Chat
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add last 6 messages for context
            for msg in conversation[-6:]:
                messages.append(msg)
            
            # Add current question
            messages.append({"role": "user", "content": user_input})
            
            print("🤖 P&ID Assistant: ", end="", flush=True)
            
            # OpenAI API Call
            response = client.chat.completions.create(
                model="gpt-4o",  # Changed to available model
                messages=messages,
            )
            
            answer = response.choices[0].message.content
            print(answer)
            print("─" * 60)
            
            # Add to conversation history
            conversation.append({"role": "user", "content": user_input})
            conversation.append({"role": "assistant", "content": answer})
            
        except KeyboardInterrupt:
            print("\n👋 Chat ended by Ctrl+C!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again...")


def AI_dexpi_change(change_request: str, dexpi_xml: str) -> tuple[str, str]:
    """
    Apply a change to a DEXPI XML using OpenAI and return (updated_xml, comment).
    Model must return UPDATED XML first, then on a new line: `COMMENT: <summary>` in English.
    No JSON. No markdown fences. No extra prose.
    """
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    system_prompt = (
        "You are an expert DEXPI/P&ID XML editor. "
        "Given a change request and a DEXPI XML document, output a valid UPDATED XML. "
        "Rules:\n"
        "- Make minimal necessary changes to satisfy the request.\n"
        "- Preserve namespaces, IDs, and existing structure when possible.\n"
        "- Ensure the result is well-formed XML and remains DEXPI-compliant.\n"
        "- Respond with TWO parts only:\n"
        "  1) The UPDATED XML document (first, and only the XML).\n"
        "  2) On a new line after the XML: `COMMENT: <one-line English summary of the change>`.\n"
        "- Do NOT include Markdown code fences or any other text before or after."
    )

    user_content = (
        "Change request (English):\n"
        f"{change_request}\n\n"
        "DEXPI XML to modify:\n"
        f"{dexpi_xml}"
    )

    # OpenAI call with fallback (no nested helpers)
    content = ""
    try:
        resp = client.chat.completions.create(
            model="gpt-5",
            temperature=0,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        content = resp.choices[0].message.content or ""
    except Exception:
        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
                temperature=0,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            content = resp.choices[0].message.content or ""
        except Exception as e:
            return dexpi_xml, f"OpenAI call failed: {e}"

    # Split XML and comment using COMMENT: marker (inline)
    idx = content.rfind("COMMENT:")
    if idx != -1:
        xml_candidate = content[:idx].rstrip()
        comment = content[idx + len("COMMENT:"):].strip()
    else:
        xml_candidate = content
        comment = ""
        print(xml_candidate)
    return xml_candidate, (comment or "no comment provided.")