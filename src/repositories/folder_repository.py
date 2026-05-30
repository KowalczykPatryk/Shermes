"""
Contains repository for managing folder entities.
Repository Design Pattern is used to abstract away database
operations from the rest of the application.
"""

from src.database.neo4j_client import Neo4jClient
from src.models.folder import Folder


class FolderRepository:
    def __init__(self, client: Neo4jClient) -> None:
        self.client = client

    def create_folder(self, parent_folder_id: str, name: str) -> Folder:
        """
        Creates a new folder with given name inside folder with given id.
        """
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (parent:Folder)
                WHERE elementId(parent) = $parent_id

                CREATE (child:Folder {
                    name: $name
                })

                CREATE (parent)-[:CONTAINS]->(child)

                RETURN elementId(child) AS id, child.name AS name
                """,
                parent_id=parent_folder_id,
                name=name,
            )

            record = result.single()

            if record is None:
                raise ValueError("Folder not found")

            return Folder(
                id=record["id"],
                name=record["name"],
            )

    def get_folder(self, folder_id: str) -> Folder:
        """
        Returns folder with given id.
        """
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (f:Folder)
                WHERE elementId(f) = $folder_id
                RETURN elementId(f) AS id, f.name AS name, f.system AS system
                """,
                folder_id=folder_id,
            )

            record = result.single()

            if record is None:
                raise ValueError("Folder not found")

            return Folder(
                id=record["id"],
                name=record["name"],
                system=record["system"],
            )

    def delete_folder(self, folder_id: str) -> None:
        """
        Deletes folder with given id and all its subfolders and cases.
        """
        with self.client.driver.session() as session:
            session.run(
                """
                MATCH (f:Folder)-[*0..]->(n)
                WHERE elementId(f) = $id
                DETACH DELETE n
                """,
                folder_id=folder_id,
            )

    def create_root_folder(self) -> Folder:
        """
        Creates root folder if it doesn't exist. Root folder is a system folder
        in which all other folders are.
        """
        with self.client.driver.session() as session:
            result = session.run(
                """
                MERGE (f:Folder {
                    system: true
                })
                ON CREATE SET f.name = "ROOT"

                RETURN elementId(f) AS id, f.name AS name
                """
            )

            record = result.single()

            if record is None:
                raise ValueError("Root folder was not created")

            return Folder(
                id=record["id"],
                name=record["name"],
                system=True,
            )

    def get_root_folder(self) -> Folder:
        """
        Returns root folder. Root folder is a system folder
        in which all other folders are.
        """
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (f:Folder)
                WHERE f.system = true
                RETURN elementId(f) AS id, f.name AS name
                """,
            )

            record = result.single()

            if record is None:
                raise ValueError("Root folder not found")

            return Folder(
                id=record["id"],
                name=record["name"],
                system=True,
            )

    def rename_folder(self, folder_id: str, new_name: str) -> None:
        """
        Changes name of the folder with given id to given new name.
        """
        with self.client.driver.session() as session:
            session.run(
                """
                MATCH (f:Folder)
                WHERE elementId(f) = $folder_id
                SET f.name = $new_name
                """,
                folder_id=folder_id,
                new_name=new_name,
            )

    def get_children(self, folder_id: str) -> list[Folder]:
        """
        Returns list of child folders of folder with given id.
        """
        with self.client.driver.session() as session:
            result = session.run(
                """
                MATCH (f:Folder)-[:CONTAINS]->(child:Folder)
                WHERE elementId(f) = $folder_id
                RETURN elementId(child) AS id, child.name AS name, child.system AS 
                system
                """,
                folder_id=folder_id,
            )

            folders = []
            for record in result:
                folders.append(
                    Folder(
                        id=record["id"],
                        name=record["name"],
                        system=record["system"],
                    )
                )

            return folders
