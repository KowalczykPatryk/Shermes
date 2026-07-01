"""
Contains repository for managing board entities.
Repository Design Pattern is used to abstract away database
operations from the rest of the application.
"""

from __future__ import annotations

from uuid import uuid4

from src.database.neo4j_client import Neo4jClient
from src.models.board_edge import BoardEdge
from src.models.board_node import BoardNode, BoardNodeDraft, BoardNodeType


class BoardRepository:
    """Repository for nodes, relationships and board layout."""

    def __init__(self, client: Neo4jClient) -> None:
        self.client = client
        self._schema_ready = False

    def ensure_schema(self) -> None:
        """Create id indexes when Neo4j permissions permit schema updates.

        The application remains usable when a managed Neo4j instance disallows
        schema administration; the queries themselves do not rely on indexes.
        """
        if self._schema_ready:
            return

        try:
            with self.client.driver.session() as session:
                session.run(
                    """
                    CREATE CONSTRAINT board_node_id_unique IF NOT EXISTS
                    FOR (node:BoardNode) REQUIRE node.id IS UNIQUE
                    """
                ).consume()
                session.run(
                    """
                    CREATE CONSTRAINT board_edge_id_unique IF NOT EXISTS
                    FOR ()-[relationship:RELATED_TO]-()
                    REQUIRE relationship.id IS UNIQUE
                    """
                ).consume()
        except Exception:
            # A lack of CREATE CONSTRAINT privileges must not prevent a user
            # from opening existing cases. Neo4j can still execute all CRUD
            # operations without these optional optimisations.
            pass
        finally:
            self._schema_ready = True

    def create_node(
        self,
        case_id: str,
        draft: BoardNodeDraft,
        *,
        x: float,
        y: float,
    ) -> BoardNode:
        """Create a node and attach it to ``case_id``."""
        self.ensure_schema()
        node_id = str(uuid4())
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (case:Case)
                WHERE elementId(case) = $case_id
                CREATE (case)-[:HAS_BOARD_NODE]->(node:BoardNode {
                    id: $node_id,
                    case_id: $case_id,
                    node_type: $node_type,
                    title: $title,
                    description: $description,
                    attachments: $attachments,
                    occurred_at: $occurred_at,
                    x: $x,
                    y: $y,
                    created_at: datetime(),
                    updated_at: datetime()
                })
                RETURN node.id AS id,
                       node.case_id AS case_id,
                       node.node_type AS node_type,
                       node.title AS title,
                       node.description AS description,
                       node.attachments AS attachments,
                       node.occurred_at AS occurred_at,
                       node.x AS x,
                       node.y AS y
                """,
                case_id=case_id,
                node_id=node_id,
                node_type=draft.node_type.value,
                title=draft.title.strip(),
                description=draft.description.strip(),
                attachments=list(draft.attachments),
                occurred_at=draft.occurred_at,
                x=float(x),
                y=float(y),
            )
            record = result.single()

        if record is None:
            raise ValueError("Case not found; board node was not created.")
        return self._node_from_record(record)

    def get_nodes(self, case_id: str) -> list[BoardNode]:
        """Return all board nodes belonging to a case in stable creation order."""
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (case:Case)-[:HAS_BOARD_NODE]->(node:BoardNode)
                WHERE elementId(case) = $case_id
                RETURN node.id AS id,
                       node.case_id AS case_id,
                       node.node_type AS node_type,
                       node.title AS title,
                       node.description AS description,
                       coalesce(node.attachments, []) AS attachments,
                       node.occurred_at AS occurred_at,
                       coalesce(node.x, 0.0) AS x,
                       coalesce(node.y, 0.0) AS y
                ORDER BY node.created_at, node.id
                """,
                case_id=case_id,
            )
            return [self._node_from_record(record) for record in result]

    def update_node(
        self, case_id: str, node_id: str, draft: BoardNodeDraft
    ) -> BoardNode:
        """Update editable node data while enforcing case ownership."""
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (:Case)-[:HAS_BOARD_NODE]->(node:BoardNode {id: $node_id})
                WHERE node.case_id = $case_id
                SET node.node_type = $node_type,
                    node.title = $title,
                    node.description = $description,
                    node.attachments = $attachments,
                    node.occurred_at = $occurred_at,
                    node.updated_at = datetime()
                RETURN node.id AS id,
                       node.case_id AS case_id,
                       node.node_type AS node_type,
                       node.title AS title,
                       node.description AS description,
                       node.attachments AS attachments,
                       node.occurred_at AS occurred_at,
                       node.x AS x,
                       node.y AS y
                """,
                case_id=case_id,
                node_id=node_id,
                node_type=draft.node_type.value,
                title=draft.title.strip(),
                description=draft.description.strip(),
                attachments=list(draft.attachments),
                occurred_at=draft.occurred_at,
            )
            record = result.single()

        if record is None:
            raise ValueError("Board node not found in this case.")
        return self._node_from_record(record)

    def update_node_position(
        self, case_id: str, node_id: str, x: float, y: float
    ) -> None:
        """Persist a drag-and-drop position without changing node content."""
        with self.client.driver.session() as session:
            session.run(
                """
                MATCH (:Case)-[:HAS_BOARD_NODE]->(node:BoardNode {id: $node_id})
                WHERE node.case_id = $case_id
                SET node.x = $x,
                    node.y = $y,
                    node.updated_at = datetime()
                """,
                case_id=case_id,
                node_id=node_id,
                x=float(x),
                y=float(y),
            ).consume()

    def delete_node(self, case_id: str, node_id: str) -> None:
        """Delete a node and all incident board relationships."""
        with self.client.driver.session() as session:
            session.run(
                """
                MATCH (:Case)-[:HAS_BOARD_NODE]->(node:BoardNode {id: $node_id})
                WHERE node.case_id = $case_id
                DETACH DELETE node
                """,
                case_id=case_id,
                node_id=node_id,
            ).consume()

    def create_edge(self, case_id: str, source_id: str, target_id: str) -> BoardEdge:
        """Create an undirected logical relation, without duplicate pairs."""
        if source_id == target_id:
            raise ValueError("A board node cannot be connected to itself.")

        self.ensure_schema()
        edge_id = str(uuid4())
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (case:Case)
                WHERE elementId(case) = $case_id
                MATCH (case)-[:HAS_BOARD_NODE]->(source:BoardNode {id: $source_id})
                MATCH (case)-[:HAS_BOARD_NODE]->(target:BoardNode {id: $target_id})
                OPTIONAL MATCH (source)-[existing:RELATED_TO]-(target)
                WHERE existing.case_id = $case_id
                WITH source, target, [edge IN collect(existing) WHERE edge IS NOT NULL] 
                AS existing_edges
                FOREACH (_ IN CASE WHEN size(existing_edges) = 0 THEN [1] ELSE [] END |
                    CREATE (source)-[:RELATED_TO {
                        id: $edge_id,
                        case_id: $case_id,
                        created_at: datetime()
                    }]->(target)
                )
                MATCH (source)-[edge:RELATED_TO]-(target)
                WHERE edge.case_id = $case_id
                RETURN edge.id AS id,
                       edge.case_id AS case_id,
                       source.id AS source_id,
                       target.id AS target_id
                ORDER BY edge.created_at
                LIMIT 1
                """,
                case_id=case_id,
                source_id=source_id,
                target_id=target_id,
                edge_id=edge_id,
            )
            record = result.single()

        if record is None:
            raise ValueError("One or both board nodes do not belong to this case.")
        return self._edge_from_record(record)

    def get_edges(self, case_id: str) -> list[BoardEdge]:
        """Return all relationships whose endpoints belong to a case."""
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (case:Case)
                WHERE elementId(case) = $case_id
                MATCH (case)-[:HAS_BOARD_NODE]->(source:BoardNode)-[edge:RELATED_TO]->(
                    target:BoardNode)
                MATCH (case)-[:HAS_BOARD_NODE]->(target)
                WHERE edge.case_id = $case_id
                RETURN edge.id AS id,
                       edge.case_id AS case_id,
                       source.id AS source_id,
                       target.id AS target_id
                """,
                case_id=case_id,
            )
            return [self._edge_from_record(record) for record in result]

    def delete_edge(self, case_id: str, edge_id: str) -> None:
        """Delete one persisted board relationship."""
        with self.client.driver.session() as session:
            session.run(
                """
                MATCH ()-[edge:RELATED_TO {id: $edge_id, case_id: $case_id}]-()
                DELETE edge
                """,
                case_id=case_id,
                edge_id=edge_id,
            ).consume()

    def clear_case_board(self, case_id: str) -> None:
        """Delete all board content attached to one case, and nothing else."""
        with self.client.driver.session() as session:
            session.run(
                """
                MATCH (case:Case)-[:HAS_BOARD_NODE]->(node:BoardNode)
                WHERE elementId(case) = $case_id
                DETACH DELETE node
                """,
                case_id=case_id,
            ).consume()

    def shortest_path(
        self,
        case_id: str,
        source_id: str,
        target_id: str,
    ) -> tuple[list[str], list[str]] | None:
        """Return the shortest path within a single case, if one exists."""
        if source_id == target_id:
            return [source_id], []

        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (case:Case)
                WHERE elementId(case) = $case_id
                MATCH (case)-[:HAS_BOARD_NODE]->(source:BoardNode {id: $source_id})
                MATCH (case)-[:HAS_BOARD_NODE]->(target:BoardNode {id: $target_id})
                MATCH path = shortestPath((source)-[:RELATED_TO*]-(target))
                WHERE ALL(path_node IN nodes(path) WHERE path_node.case_id = $case_id)
                AND ALL(relationship IN relationships(path)
                        WHERE relationship.case_id = $case_id)
                RETURN [path_node IN nodes(path) | path_node.id] AS node_ids,
                       [relationship IN relationships(path) | relationship.id] 
                       AS edge_ids
                LIMIT 1
                """,
                case_id=case_id,
                source_id=source_id,
                target_id=target_id,
            )
            record = result.single()

        if record is None:
            return None
        return list(record["node_ids"]), list(record["edge_ids"])

    @staticmethod
    def _node_from_record(record) -> BoardNode:
        """
        Convert a Neo4j record to a BoardNode, with fallback for unknown node types.
        """
        try:
            node_type = BoardNodeType(record["node_type"])
        except ValueError:
            node_type = BoardNodeType.NOTE

        return BoardNode(
            id=record["id"],
            case_id=record["case_id"],
            node_type=node_type,
            title=record["title"],
            description=record["description"] or "",
            attachments=tuple(record["attachments"] or ()),
            occurred_at=record["occurred_at"],
            x=float(record["x"] or 0.0),
            y=float(record["y"] or 0.0),
        )

    @staticmethod
    def _edge_from_record(record) -> BoardEdge:
        """Convert a Neo4j record to a BoardEdge."""
        return BoardEdge(
            id=record["id"],
            case_id=record["case_id"],
            source_id=record["source_id"],
            target_id=record["target_id"],
        )
