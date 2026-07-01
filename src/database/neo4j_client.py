"""Neo4j driver configuration used by all repositories."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


class Neo4jClient:
    """
    Small wrapper around the official Neo4j driver.

    Uses environment variables to configure the connection.
    They are suggested to be set in a .env file in the project root.
    """

    def __init__(self) -> None:
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(
                os.getenv("NEO4J_USERNAME", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "password"),
            ),
        )

    def close(self) -> None:
        self.driver.close()
