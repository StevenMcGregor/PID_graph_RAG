import json
import os
import sys
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Iterable, Tuple


def _console_print(msg: str) -> None:
    print(msg, flush=True)


def _load_env() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        # dotenv is optional; environment variables can be provided by the shell
        pass


def _safe_as_dict(value: Any) -> Dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
        try:
            return value.model_dump()  # pydantic v2
        except Exception:
            pass
    if hasattr(value, "dict") and callable(getattr(value, "dict")):
        try:
            return value.dict()  # pydantic v1
        except Exception:
            pass
    if isinstance(value, dict):
        return value
    try:
        json.dumps(value)
        return {"value": value}
    except Exception:
        return {"repr": repr(value)}


def load_dexpi_model(xml_path: str) -> Any:
    """Attempt to load a DEXPI XML using pyDEXPI.

    Tries multiple import paths/APIs to be resilient across pyDEXPI versions.
    """
    last_error: Exception | None = None

    # Attempt 1: Known current location (pydexpi 1.0.0): loaders.proteus_serializer
    try:
        from pydexpi.loaders.proteus_serializer import ProteusSerializer  # type: ignore

        _console_print("Using pydexpi.loaders.proteus_serializer.ProteusSerializer ...")
        serializer = ProteusSerializer()
        if hasattr(serializer, "load"):
            # Try two-argument signature: (dir_path, filename)
            try:
                dir_path, filename = os.path.split(os.path.abspath(xml_path))
                if not dir_path:
                    dir_path = "."
                return serializer.load(dir_path=dir_path, filename=filename)
            except TypeError:
                # Fallback: single path
                return serializer.load(xml_path)
    except Exception as e:  # noqa: BLE001
        last_error = e

    # Attempt 2: DexpiLoader (some docs reference this)
    try:
        from pydexpi import DexpiLoader  # type: ignore

        _console_print("Using pydexpi.DexpiLoader ...")
        return DexpiLoader.load(xml_path)
    except Exception as e:  # noqa: BLE001
        last_error = e

    # Attempt 3: Other historical locations of ProteusSerializer
    for mod_name in [
        "pydexpi.proteus.serializer",
        "pydexpi.proteus",
        "pydexpi",
    ]:
        try:
            mod = __import__(mod_name, fromlist=["ProteusSerializer"])  # type: ignore
            ProteusSerializer = getattr(mod, "ProteusSerializer")
            _console_print(f"Using {mod_name}.ProteusSerializer ...")
            serializer = ProteusSerializer()
            for method_name in ("load", "read", "parse"):
                if hasattr(serializer, method_name):
                    return getattr(serializer, method_name)(xml_path)
            for method_name in ("load", "read", "parse"):
                if hasattr(ProteusSerializer, method_name):
                    return getattr(ProteusSerializer, method_name)(xml_path)
        except Exception as e:  # noqa: BLE001
            last_error = e

    raise RuntimeError(
        "Unable to load DEXPI XML. Ensure 'pydexpi' is installed and compatible."
    ) from last_error


def to_networkx_graph(model: Any):
    # Strategy 1: pydexpi 1.0.0 MLGraphLoader
    try:
        from pydexpi.loaders.ml_graph_loader import MLGraphLoader  # type: ignore

        _console_print("Building NetworkX graph via pydexpi.loaders.ml_graph_loader.MLGraphLoader ...")
        loader = MLGraphLoader()
        if hasattr(loader, "dexpi_to_graph"):
            return loader.dexpi_to_graph(model)
        if hasattr(loader, "parse_dexpi_to_graph"):
            return loader.parse_dexpi_to_graph(model)
    except Exception:
        pass

    # Strategy 2: model provides to_graph()
    if hasattr(model, "to_graph") and callable(getattr(model, "to_graph")):
        _console_print("Building NetworkX graph via model.to_graph() ...")
        return model.to_graph()

    # Strategy 3: Other historical locations
    for mod_name, cls_name in [
        ("pydexpi.loaders", "MLGraphLoader"),
        ("pydexpi", "MLGraphLoader"),
    ]:
        try:
            mod = __import__(mod_name, fromlist=[cls_name])  # type: ignore
            MLGraphLoader = getattr(mod, cls_name)
            _console_print(f"Building NetworkX graph via {mod_name}.{cls_name} ...")
            loader = MLGraphLoader()
            return loader.load(model)
        except Exception:
            continue

    raise RuntimeError(
        "Could not construct a NetworkX graph from the parsed model."
    )


def _flatten_for_neo4j(props: Dict[str, Any]) -> Dict[str, Any]:
    flat: Dict[str, Any] = {}
    for k, v in props.items():
        key = str(k)
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            flat[key] = v
        elif isinstance(v, (list, tuple)):
            try:
                json.dumps(v)
                flat[key] = v
            except Exception:
                flat[key] = [repr(x) for x in v]
        elif isinstance(v, dict):
            # Neo4j supports nested maps, but keeping one-level props is simpler
            try:
                json.dumps(v)
                flat[key] = v
            except Exception:
                flat[key] = {sk: repr(sv) for sk, sv in v.items()}
        else:
            flat[key] = repr(v)
    return flat


def iter_nodes_edges(graph: Any) -> Tuple[Iterable[Tuple[str, Dict[str, Any]]], Iterable[Tuple[str, str, Dict[str, Any]]]]:
    # Expect a NetworkX-like API
    try:
        nodes_iter = graph.nodes(data=True)  # type: ignore[attr-defined]
        edges_iter = graph.edges(data=True)  # type: ignore[attr-defined]
        return nodes_iter, edges_iter
    except Exception as exc:  # noqa: BLE001
        raise TypeError("Expected a NetworkX graph-like object.") from exc


def load_graph_to_neo4j(graph: Any, uri: str, user: str, password: str) -> None:
    from neo4j import GraphDatabase  # type: ignore

    driver = GraphDatabase.driver(uri, auth=(user, password))
    nodes_iter, edges_iter = iter_nodes_edges(graph)

    def _batched(iterable, size: int):
        batch = []
        for item in iterable:
            batch.append(item)
            if len(batch) >= size:
                yield batch
                batch = []
        if batch:
            yield batch

    # Use MERGE to avoid duplicates; index on :Component(id) is recommended
    create_node_cypher = (
        "MERGE (n:Component {id: row.id}) "
        "SET n += row.props "
        "SET n.type = coalesce(row.props.type, n.type)"
    )
    create_rel_cypher = (
        "MATCH (a:Component {id: row.src}), (b:Component {id: row.tgt}) "
        "MERGE (a)-[r:CONNECTED_TO]->(b) "
        "SET r += row.props"
    )

    with driver.session() as session:
        # Optional: create an index for performance
        try:
            session.run("CREATE INDEX component_id IF NOT EXISTS FOR (n:Component) ON (n.id)")
        except Exception:
            pass

        # Nodes
        for batch in _batched(nodes_iter, 500):
            def _coerce_node(item: Tuple[Any, Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
                node_id_raw, data = item
                node_id = str(node_id_raw)
                props = _flatten_for_neo4j(_safe_as_dict(data))
                props.setdefault("id", node_id)
                return node_id, props

            payload = [{"id": nid, "props": props} for nid, props in map(_coerce_node, batch)]
            session.run("UNWIND $rows AS row " + create_node_cypher, rows=payload)

        # Relationships
        for batch in _batched(edges_iter, 500):
            def _coerce_edge(item: Tuple[Any, Any, Dict[str, Any]]):
                src_raw, tgt_raw, data = item
                props = _flatten_for_neo4j(_safe_as_dict(data))
                return str(src_raw), str(tgt_raw), props

            payload = [
                {"src": s, "tgt": t, "props": p} for s, t, p in map(_coerce_edge, batch)
            ]
            session.run("UNWIND $rows AS row " + create_rel_cypher, rows=payload)

    driver.close()


def export_graphml(graph: Any, out_path: str) -> None:
    try:
        import json
        from enum import Enum, EnumMeta
        import networkx as nx  # type: ignore

        def _coerce_value(value: Any) -> Any:
            # None → drop
            if value is None:
                return None
            # Primitives
            if isinstance(value, (str, int, float, bool)):
                return value
            # Enum instance → name
            if isinstance(value, Enum):
                return value.name
            # Enum class/type → its __name__
            if isinstance(value, type) and issubclass(value, Enum):  # type: ignore[arg-type]
                return value.__name__
            # Containers → recurse
            if isinstance(value, dict):
                out: dict[str, Any] = {}
                for k, v in value.items():
                    ck = str(k)
                    cv = _coerce_value(v)
                    if cv is not None:
                        out[ck] = cv
                return out
            if isinstance(value, (list, tuple, set)):
                out_list = []
                for v in value:
                    cv = _coerce_value(v)
                    if cv is not None:
                        out_list.append(cv)
                return out_list
            # Fallback: JSON if possible, else str
            try:
                return json.dumps(value, default=lambda o: o.name if isinstance(o, Enum) else str(o))
            except Exception:
                return str(value)

        # Build a sanitized copy graph with only GraphML-safe values
        is_directed = nx.is_directed(graph)
        is_multi = graph.is_multigraph() if hasattr(graph, "is_multigraph") else False
        if is_multi and is_directed:
            H = nx.MultiDiGraph()
        elif is_multi:
            H = nx.MultiGraph()
        elif is_directed:
            H = nx.DiGraph()
        else:
            H = nx.Graph()

        # Graph attributes
        for k, v in getattr(graph, "graph", {}).items():
            cv = _coerce_value(v)
            if cv is not None:
                H.graph[str(k)] = cv

        # Nodes
        for n, data in graph.nodes(data=True):
            sanitized: dict[str, Any] = {}
            for k, v in data.items():
                cv = _coerce_value(v)
                if cv is not None:
                    sanitized[str(k)] = cv
            H.add_node(str(n), **sanitized)

        # Edges
        if is_multi:
            for u, v, key, data in graph.edges(keys=True, data=True):
                sanitized: dict[str, Any] = {}
                for k, v2 in data.items():
                    cv = _coerce_value(v2)
                    if cv is not None:
                        sanitized[str(k)] = cv
                H.add_edge(str(u), str(v), key=str(key), **sanitized)
        else:
            for u, v, data in graph.edges(data=True):
                sanitized: dict[str, Any] = {}
                for k, v2 in data.items():
                    cv = _coerce_value(v2)
                    if cv is not None:
                        sanitized[str(k)] = cv
                H.add_edge(str(u), str(v), **sanitized)

        # As an extra guard, force-convert any residual Enum values to strings just before write
        def _final_sanitize():
            from enum import Enum
            for k, v in list(H.graph.items()):
                if isinstance(v, Enum) or isinstance(v, type) and hasattr(v, "__members__"):
                    H.graph[k] = str(v)
            for n, data in H.nodes(data=True):
                for k, v in list(data.items()):
                    if isinstance(v, Enum) or isinstance(v, type) and hasattr(v, "__members__"):
                        data[k] = str(v)
            for u, v, data in H.edges(data=True):
                for k, val in list(data.items()):
                    if isinstance(val, Enum) or isinstance(val, type) and hasattr(val, "__members__"):
                        data[k] = str(val)

        _final_sanitize()
        nx.write_graphml(H, out_path)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to write GraphML to {out_path}: {exc}") from exc


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Convert a DEXPI P&ID XML into a NetworkX graph and optionally load into Neo4j."
        )
    )
    parser.add_argument("xml", help="Path to DEXPI XML file")
    parser.add_argument(
        "--graphml",
        default=None,
        help="Optional path to export the graph as GraphML",
    )
    parser.add_argument(
        "--load-neo4j",
        action="store_true",
        help="If set, load the graph into Neo4j using environment variables",
    )
    parser.add_argument(
        "--neo4j-uri",
        default=None,
        help="Neo4j bolt URI (defaults to NEO4J_URI env)",
    )
    parser.add_argument(
        "--neo4j-user",
        default=None,
        help="Neo4j username (defaults to NEO4J_USER env)",
    )
    parser.add_argument(
        "--neo4j-password",
        default=None,
        help="Neo4j password (defaults to NEO4J_PASSWORD env)",
    )

    args = parser.parse_args(argv)

    _load_env()

    xml_path = args.xml
    if not os.path.isfile(xml_path):
        _console_print(f"ERROR: XML file not found: {xml_path}")
        return 2

    _console_print("Parsing DEXPI XML ...")
    model = load_dexpi_model(xml_path)

    _console_print("Generating NetworkX graph ...")
    graph = to_networkx_graph(model)

    if args.graphml:
        export_graphml(graph, args.graphml)
        _console_print(f"GraphML exported to: {args.graphml}")

    if args.load_neo4j:
        uri = args.neo4j_uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = args.neo4j_user or os.getenv("NEO4J_USER", "neo4j")
        password = args.neo4j_password or os.getenv("NEO4J_PASSWORD", "neo4j")
        _console_print(f"Loading graph to Neo4j at {uri} ...")
        load_graph_to_neo4j(graph, uri=uri, user=user, password=password)
        _console_print("Graph successfully loaded to Neo4j.")

    _console_print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


