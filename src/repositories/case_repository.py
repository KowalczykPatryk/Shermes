"""
Contains repository for managing case entities.
Repository Design Pattern is used to abstract away database
operations from the rest of the application.
"""

from src.database.neo4j_client import Neo4jClient
from src.models.case import Case


class CaseRepository:
    def __init__(self, client: Neo4jClient) -> None:
        self.client = client

    def create_case(self, folder_id: str, case_name: str) -> Case:
        """
        Creates a new case with given name inside folder with given id.
        """

        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (f:Folder)
                WHERE elementId(f) = $folder_id

                CREATE (c:Case {
                    name: $case_name
                })

                CREATE (f)-[:CONTAINS]->(c)
                RETURN elementId(c) AS id, c.name AS name
                """,
                folder_id=folder_id,
                case_name=case_name,
            )
            record = result.single()
            if record is None:
                raise ValueError("Case not found")

            return Case(
                id=record["id"],
                name=record["name"],
            )

    def delete_case(self, case_id: str) -> None:
        """
        Deletes case with given id from the database.
        """
        with self.client.driver.session() as session:
            session.run(
                """
                MATCH (c:Case)
                WHERE elementId(c) = $case_id

                DETACH DELETE c
                """,
                case_id=case_id,
            )

    def rename_case(self, case_id: str, new_name: str) -> None:
        """
        Changes name of the case with given id to given new name.
        """
        with self.client.driver.session() as session:
            session.run(
                """
                MATCH (c:Case)
                WHERE elementId(c) = $case_id

                SET c.name = $new_name
                """,
                case_id=case_id,
                new_name=new_name,
            )

    def get_case(self, case_id: str) -> Case:
        """
        Returns case with given id.
        """
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Case)
                WHERE elementId(c) = $case_id
                RETURN elementId(c) AS id, c.name AS name
                """,
                case_id=case_id,
            )

            record = result.single()

            if record is None:
                raise ValueError("Case not found")

            return Case(
                id=record["id"],
                name=record["name"],
            )

    def get_cases_in_folder(self, folder_id: str) -> list[Case]:
        """
        Returns list of cases that are directly inside folder with given id.
        """
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (f:Folder)-[:CONTAINS]->(c:Case)
                WHERE elementId(f) = $folder_id
                RETURN elementId(c) AS id, c.name AS name
                """,
                folder_id=folder_id,
            )

            cases = []
            for record in result:
                cases.append(
                    Case(
                        id=record["id"],
                        name=record["name"],
                    )
                )

            return cases
