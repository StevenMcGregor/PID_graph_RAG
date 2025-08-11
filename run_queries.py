import os
import sys
from typing import List


def _load_env() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        pass


def _read_queries_from_file(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Remove line comments starting with // or #
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("#"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)

    # Split on semicolon; naive but fine for simple sample queries
    parts = [p.strip() for p in cleaned.split(";")]
    return [p for p in parts if p]


def run_queries(queries: List[str], uri: str, user: str, password: str) -> None:
    from neo4j import GraphDatabase  # type: ignore

    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        for i, q in enumerate(queries, start=1):
            print(f"\n--- Query {i} ---\n{q}\n", flush=True)
            try:
                result = session.run(q)
                records = list(result)
                print(f"Rows: {len(records)}", flush=True)
                for rec in records[:50]:  # avoid flooding console
                    print(rec.data(), flush=True)
                if len(records) > 50:
                    print(f"... truncated {len(records) - 50} rows", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"Error: {exc}", flush=True)
    driver.close()


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run sample Cypher queries against a Neo4j database."
    )
    parser.add_argument(
        "--file",
        default="sample_queries.cypher",
        help="Path to a .cypher file with semicolon-separated statements",
    )
    parser.add_argument("--neo4j-uri", default=None, help="Neo4j bolt URI")
    parser.add_argument("--neo4j-user", default=None, help="Neo4j username")
    parser.add_argument("--neo4j-password", default=None, help="Neo4j password")

    args = parser.parse_args(argv)
    _load_env()

    uri = args.neo4j_uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = args.neo4j_user or os.getenv("NEO4J_USER", "neo4j")
    password = args.neo4j_password or os.getenv("NEO4J_PASSWORD", "neo4j")

    queries = _read_queries_from_file(args.file)
    if not queries:
        print(f"No queries found in {args.file}", flush=True)
        return 2

    run_queries(queries, uri=uri, user=user, password=password)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


