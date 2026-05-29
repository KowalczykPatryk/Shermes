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
* drag & drop

Form:

* Desktop application

Stack:

* Neo4j
* PySide6

Development setup is described in the dev_setup/README.md

