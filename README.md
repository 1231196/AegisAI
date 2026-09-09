<p align="center">
  <img src="./docs/logo.png" alt="Aegis AI Logo" width="400">
</p>

<p align="center">
An Enterprise AI Platform for Technical Support powered by RAG, AI Agents and Model Context Protocol (MCP).
</p>

<p align="center">

![Status](https://img.shields.io/badge/status-In%20Development-32CD32)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

</p>

---

# Overview

Aegis AI is an enterprise-oriented AI platform designed to demonstrate modern AI Engineering practices.

The project combines Retrieval-Augmented Generation (RAG), AI Agents, Tool Calling, and the Model Context Protocol (MCP) to build an intelligent technical support assistant capable of understanding documentation, interacting with enterprise systems, and assisting users through natural language.

This project is being developed as a portfolio project to showcase scalable software architecture, modern AI development, and production-ready engineering practices.

---

# Project Goals

- Build a production-ready AI architecture
- Implement an advanced RAG pipeline
- Develop autonomous AI Agents
- Integrate external tools using MCP
- Support multi-tenant organizations
- Secure AI interactions through RBAC and approval workflows
- Demonstrate AI observability and evaluation

---

# Planned Features

### Authentication

- JWT Authentication
- User Registration
- Organizations
- Role-Based Access Control

### Knowledge Base

- PDF Upload
- DOCX Support
- Markdown Support
- Automatic Chunking
- Embeddings
- Vector Search

### AI Chat

- Conversational Assistant
- Source Attribution
- Conversation History
- Streaming Responses

### AI Agents

- Tool Calling
- Autonomous Reasoning
- External Integrations
- Approval Workflows

### MCP

- MCP Server
- Secure Tool Execution
- Extensible Tool Registry

### Observability

- Request Monitoring
- Token Usage
- Cost Estimation
- Performance Metrics

---

# Planned Architecture

```
                    React Frontend

                           │

                     FastAPI Backend

                           │

        ┌──────────────────┼──────────────────┐

        │                  │                  │

     Authentication      AI Agent         RAG Pipeline

        │                  │                  │

        └──────────────┬───┴──────────────────┘

                       │

                  MCP Tool Server

                       │

        ┌──────────────┼──────────────┐

        │              │              │

     Knowledge      Ticketing      External APIs

                       │

        PostgreSQL • Redis • Qdrant
```

---

# Technology Stack

## Frontend

- React
- TypeScript
- Tailwind CSS
- shadcn/ui

## Backend

- Python
- FastAPI
- SQLAlchemy
- Alembic

## Artificial Intelligence

- RAG
- AI Agents
- MCP
- Tool Calling
- LLMs
- Embeddings

## Databases

- PostgreSQL
- Qdrant
- Redis

## Infrastructure

- Docker
- Docker Compose

---

# Project Structure

```
aegis-ai/

├── backend/
│   ├── app/
│   ├── api/
│   ├── auth/
│   ├── agents/
│   ├── rag/
│   ├── mcp/
│   └── core/
│
├── frontend/
│
├── docs/
│
├── docker/
│
├── tests/
│
└── README.md
```

---

# Development Roadmap

## Phase 1

- [x] Authentication
- [x] Organizations
- [x] PostgreSQL
- [x] React Frontend
- [x] Docker Environment

## Phase 2

- [x] Document Upload
- [x] RAG Pipeline
- [x] AI Chat
- [x] Conversation History

## Phase 3

- [ ] AI Agents
- [ ] MCP Integration
- [ ] Tool Calling
- [ ] Approval Workflows

## Phase 4

- [ ] Observability
- [ ] AI Evaluation
- [ ] Multi-model Routing
- [ ] Production Deployment

---

# Current Status

🚧 This project is currently under active development.

The initial focus is on building a clean, scalable architecture that will support advanced AI capabilities in future iterations.

---

# Author

**Rodrigo Faria**

AI Engineering • Software Engineering • Cybersecurity
