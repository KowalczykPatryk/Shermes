# Shermes
The application features an interactive investigation board inspired by evidence boards and conspiracy boards used in detective investigations, allowing users to visually connect people, events, locations, documents, and other entities through relationships and timelines.
 
The name comes from **Sher**lock Hol**mes**, because it is handy tool for detective (Police Detective or Private Investigator) .

<img width="297" height="170" alt="image" src="https://github.com/user-attachments/assets/587a1e2c-a603-4f18-9cfc-4c564bf91de9" />
<img width="300" height="168" alt="image" src="https://github.com/user-attachments/assets/3b9a911d-563b-4c00-9d34-4ac26f349c62" />

Project idea:  

An investigation board with photos, notes, people, events, and places connected by red lines. The user creates people, places, events, evidence, phones, documents, organizations, vehicles, and hypotheses, then links them with relationships. The application is meant to help uncover connections between facts that do not appear related at first glance. The user can, for example, select two people and the system will search for the shortest path between them, or identify the person with the highest number of indirect connections. A node can contain photos, PDFs, notes, links, and timestamps. The system arranges events chronologically and shows who was where and when. Information can be searched and filtered.

Views:

* browsing directories of different cases
* main canvas (investigation board)
* timeline view

Functionality:

* creating a directory for a new case
* adding new nodes and edges
* editing existing nodes and edges
* visualizing them on the board
* searching and filtering information

Form:

* Desktop application

Stack:

* Neo4j
* PySide6

Development setup is described in the dev_setup/README.md  
Database setup is described in the db_setup/README.md


Names explained:
- neo4j_shermes - name of the Docker container
- neo4j_shermes_data - name of the Docker volume
- neo4j - name of the Neo4j database

### UI Screenshots:

<img width="1004" height="840" alt="Screenshot from 2026-07-01 23-27-31" src="https://github.com/user-attachments/assets/2f6b6dda-f48b-4e8d-9144-61506de8b500" />
<img width="1004" height="840" alt="Screenshot from 2026-07-01 23-27-38" src="https://github.com/user-attachments/assets/03da4ca7-ff6c-4add-9c0b-f8d9f6f4a4ef" />
<img width="1004" height="840" alt="Screenshot from 2026-07-01 23-28-49" src="https://github.com/user-attachments/assets/ec0d5f81-f692-4e3e-ad86-ae82040421b2" />
<img width="1004" height="840" alt="Screenshot from 2026-07-01 23-37-46" src="https://github.com/user-attachments/assets/29421e4e-cc72-462f-b26c-af010375ca69" />
<img width="1004" height="840" alt="Screenshot from 2026-07-01 23-38-00" src="https://github.com/user-attachments/assets/478b29f3-00fb-48ff-8fac-838dfae512ca" />
<img width="1004" height="840" alt="Screenshot from 2026-07-01 23-38-05" src="https://github.com/user-attachments/assets/547e895f-1fe6-43ea-9dff-1bc0ad2c32f9" />

### Database graph:

<img width="388" height="389" alt="Screenshot from 2026-07-01 22-46-27" src="https://github.com/user-attachments/assets/0e04e134-96c6-4ba1-ba9a-519bddb53910" />
<img width="1440" height="560" alt="Screenshot from 2026-07-01 22-50-07" src="https://github.com/user-attachments/assets/a8fc77ec-ee42-4463-8c71-cc1a6e560226" />


