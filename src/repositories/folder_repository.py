"""Repository for folder entities."""

from src.database.neo4j_client import Neo4jClient
from src.models.folder import Folder


class FolderRepository:
    def __init__(self, client: Neo4jClient) -> None:
        self.client = client

    def create_folder(self, parent_folder_id: str, name: str) -> Folder:
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (parent:Folder)
                WHERE elementId(parent) = $parent_id
                CREATE (child:Folder {name: $name})
                CREATE (parent)-[:CONTAINS]->(child)
                RETURN elementId(child) AS id, child.name AS name
                """,
                parent_id=parent_folder_id,
                name=name,
            )
            record = result.single()

        if record is None:
            raise ValueError("Folder not found.")
        return Folder(id=record["id"], name=record["name"])

    def get_folder(self, folder_id: str) -> Folder:
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (folder:Folder)
                WHERE elementId(folder) = $folder_id
                RETURN elementId(folder) AS id,
                       folder.name AS name,
                       coalesce(folder.system, false) AS system
                """,
                folder_id=folder_id,
            )
            record = result.single()

        if record is None:
            raise ValueError("Folder not found.")
        return Folder(id=record["id"], name=record["name"], system=record["system"])

    def delete_folder(self, folder_id: str) -> None:
        """Delete a folder tree and board nodes attached to contained cases."""
        with self.client.driver.session() as session:
            # Cases are removed in the next statement; remove their separate
            # board-node subgraphs first so DETACH DELETE does not leave them.
            session.run(
                """
                MATCH (folder:Folder)-[:CONTAINS*0..]->(case:Case)
                WHERE elementId(folder) = $folder_id
                MATCH (case)-[:HAS_BOARD_NODE]->(board_node:BoardNode)
                WITH DISTINCT board_node
                DETACH DELETE board_node
                """,
                folder_id=folder_id,
            ).consume()
            session.run(
                """
                MATCH (folder:Folder)-[:CONTAINS*0..]->(contained)
                WHERE elementId(folder) = $folder_id
                WITH DISTINCT contained
                DETACH DELETE contained
                """,
                folder_id=folder_id,
            ).consume()

    def create_root_folder(self) -> Folder:
        with self.client.driver.session() as session:
            result = session.run(
                """
                MERGE (folder:Folder {system: true})
                ON CREATE SET folder.name = "ROOT"
                RETURN elementId(folder) AS id, folder.name AS name
                """
            )
            record = result.single()

        if record is None:
            raise ValueError("Root folder was not created.")
        return Folder(id=record["id"], name=record["name"], system=True)

    def get_root_folder(self) -> Folder:
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (folder:Folder {system: true})
                RETURN elementId(folder) AS id, folder.name AS name
                """
            )
            record = result.single()

        if record is None:
            raise ValueError("Root folder not found.")
        return Folder(id=record["id"], name=record["name"], system=True)

    def rename_folder(self, folder_id: str, new_name: str) -> None:
        with self.client.driver.session() as session:
            session.run(
                """
                MATCH (folder:Folder)
                WHERE elementId(folder) = $folder_id
                SET folder.name = $new_name
                """,
                folder_id=folder_id,
                new_name=new_name,
            ).consume()

    def get_children(self, folder_id: str) -> list[Folder]:
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (folder:Folder)-[:CONTAINS]->(child:Folder)
                WHERE elementId(folder) = $folder_id
                RETURN elementId(child) AS id,
                       child.name AS name,
                       coalesce(child.system, false) AS system
                ORDER BY child.name
                """,
                folder_id=folder_id,
            )
            return [
                Folder(id=record["id"], name=record["name"], system=record["system"])
                for record in result
            ]
