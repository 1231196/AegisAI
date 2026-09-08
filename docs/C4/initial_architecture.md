                           +----------------------+
                           |   React Frontend     |
                           |      (ReactJS)       |
                           +----------+-----------+
                                      |
                               REST / WebSocket
                                      |
                           +----------v-----------+
                           |   FastAPI Backend    |
                           |----------------------|
                           | - JWT Authentication |
                           | - Organizations      |
                           | - Users              |
                           | - Roles / RBAC       |
                           | - Document Management|
                           | - Chat Sessions      |
                           | - Conversation Mgmt  |
                           | - Audit Logs         |
                           +----+-----------+-----+
                                |           |
                 CRUD / Metadata |           | AI Requests
                                |           |
                    +-----------v--+    +---v------------------+
                    | PostgreSQL   |    |   FastAPI AI         |
                    |--------------|    |-----------------------|
                    | Users        |    | - Document Parsing    |
                    | Organizations|    | - Chunking            |
                    | Documents    |    | - Embeddings          |
                    | Chats        |    | - RAG Pipeline        |
                    | Metadata     |    | - AI Agents           |
                    +--------------+    | - Prompt Builder      |
                                        | - Model Router        |
                                        | - Conversation Memory |
                                        | - Tool Calling        |
                                        +-----+-----------+-----+
                                              |           |
                              Semantic Search |           | MCP Tools
                                              |           |
                                     +--------v--+   +----v-------------+
                                     |  Qdrant   |   |   MCP Server      |
                                     |-----------|   |-------------------|
                                     | Embeddings|   | knowledge.search()|
                                     | Chunks    |   | orders.search()   |
                                     +-----------+   | users.search()    |
                                                     | tickets.create()  |
                                                     | logs.search()     |
                                                     +---------+----------+
                                                               |
                                                       External Systems


                    +------------------+      +----------------------+
                    |      Redis       |      |   LLM Provider(s)    |
                    |------------------|      | GPT / Claude / etc.  |
                    | Sessions         |      +----------------------+
                    | Response Cache   |                 ^
                    | Embedding Cache  |                 |
                    +------------------+                 |
                                                         |
                                                FastAPI AI