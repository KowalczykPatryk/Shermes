"""Repository for case entities and their case-owned board data."""

from src.database.neo4j_client import Neo4jClient
from src.models.case import Case


class CaseRepository:
    def __init__(self, client: Neo4jClient) -> None:
        self.client = client

    def create_case(self, folder_id: str, case_name: str) -> Case:
        """Create a case inside a folder."""
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (folder:Folder)
                WHERE elementId(folder) = $folder_id
                CREATE (case:Case {name: $case_name})
                CREATE (folder)-[:CONTAINS]->(case)
                RETURN elementId(case) AS id, case.name AS name
                """,
                folder_id=folder_id,
                case_name=case_name,
            )
            record = result.single()

        if record is None:
            raise ValueError("Parent folder not found.")
        return Case(id=record["id"], name=record["name"])

    def delete_case(self, case_id: str) -> None:
        """Delete a case together with every board node and relationship it owns."""
        with self.client.driver.session() as session:
            # Delete board nodes first. Detaching them also removes RELATED_TO
            # edges, leaving no orphan investigation data after the case goes.
            session.run(
                """
                MATCH (case:Case)-[:HAS_BOARD_NODE]->(board_node:BoardNode)
                WHERE elementId(case) = $case_id
                DETACH DELETE board_node
                """,
                case_id=case_id,
            ).consume()
            session.run(
                """
                MATCH (case:Case)
                WHERE elementId(case) = $case_id
                DETACH DELETE case
                """,
                case_id=case_id,
            ).consume()

    def rename_case(self, case_id: str, new_name: str) -> None:
        """Change the displayed case name."""
        with self.client.driver.session() as session:
            session.run(
                """
                MATCH (case:Case)
                WHERE elementId(case) = $case_id
                SET case.name = $new_name
                """,
                case_id=case_id,
                new_name=new_name,
            ).consume()

    def get_case(self, case_id: str) -> Case:
        """Return one case."""
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (case:Case)
                WHERE elementId(case) = $case_id
                RETURN elementId(case) AS id, case.name AS name
                """,
                case_id=case_id,
            )
            record = result.single()

        if record is None:
            raise ValueError("Case not found.")
        return Case(id=record["id"], name=record["name"])

    def get_cases_in_folder(self, folder_id: str) -> list[Case]:
        """Return cases directly contained by a folder."""
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (folder:Folder)-[:CONTAINS]->(case:Case)
                WHERE elementId(folder) = $folder_id
                RETURN elementId(case) AS id, case.name AS name
                ORDER BY case.name
                """,
                folder_id=folder_id,
            )
            return [Case(id=record["id"], name=record["name"]) for record in result]
