# Simple DEXPI utilities
import os
from typing import Any


def load_dexpi_model(xml_path: str) -> Any:
    """Load DEXPI XML file"""
    try:
        from pydexpi.loaders.proteus_serializer import ProteusSerializer
        print("Using ProteusSerializer...")
        serializer = ProteusSerializer()
        try:
            dir_path, filename = os.path.split(os.path.abspath(xml_path))
            return serializer.load(dir_path=dir_path or ".", filename=filename)
        except TypeError:
            return serializer.load(xml_path)
    except Exception:
        raise RuntimeError("Cannot load DEXPI XML. Check if pydexpi is installed.")


def to_networkx_graph(model: Any):
    """Convert DEXPI model to NetworkX graph"""
    try:
        from pydexpi.loaders.ml_graph_loader import MLGraphLoader
        print("Creating NetworkX graph...")
        loader = MLGraphLoader()
        if hasattr(loader, "dexpi_to_graph"):
            return loader.dexpi_to_graph(model)
        return loader.parse_dexpi_to_graph(model)
    except Exception:
        raise RuntimeError("Cannot create NetworkX graph.")


def export_graphml(graph: Any, out_path: str) -> None:
    """Export graph to GraphML format - custom implementation"""
    
    # Write GraphML manually to avoid enum issues
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n')
        f.write('  <key id="node_id" for="node" attr.name="id" attr.type="string"/>\n')
        f.write('  <key id="node_name" for="node" attr.name="name" attr.type="string"/>\n')
        f.write('  <key id="node_type" for="node" attr.name="type" attr.type="string"/>\n')
        f.write('  <key id="edge_type" for="edge" attr.name="type" attr.type="string"/>\n')
        f.write('  <graph id="G" edgedefault="directed">\n')
        
        # Write nodes
        for node_id, attrs in graph.nodes(data=True):
            f.write(f'    <node id="{node_id}">\n')
            f.write(f'      <data key="node_id">{node_id}</data>\n')
            
            # Add some key attributes
            name = attrs.get('name', attrs.get('id', str(node_id)))
            f.write(f'      <data key="node_name">{str(name)}</data>\n')
            
            node_type = attrs.get('type', attrs.get('class', 'unknown'))
            f.write(f'      <data key="node_type">{str(node_type)}</data>\n')
            
            f.write('    </node>\n')
        
        # Write edges
        for src, dst, attrs in graph.edges(data=True):
            f.write(f'    <edge source="{src}" target="{dst}">\n')
            edge_type = attrs.get('type', 'CONNECTED_TO')
            f.write(f'      <data key="edge_type">{str(edge_type)}</data>\n')
            f.write('    </edge>\n')
        
        f.write('  </graph>\n')
        f.write('</graphml>\n')
