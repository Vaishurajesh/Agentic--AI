# Autonomous Document Agent 

## Overview

Autonomous Document Agent is a personal Agentic AI project built with Python and FastAPI. It accepts a natural language request, autonomously plans the execution, generates structured document content using an LLM, performs self-reflection to validate the output, and produces a polished Microsoft Word (.docx) document.

The project demonstrates how AI agents can plan, reason, evaluate, and improve their own outputs before delivering the final result.

---

## Features

* Multi-step AI agent workflow
* Task planning and orchestration
* Intelligent document structure generation
* LLM-powered content generation
* Reflection and self-evaluation of generated content
* Automatic revision of low-quality sections
* DOCX document generation
* REST API built with FastAPI
* Offline fallback mode when an API key is unavailable

---

## Architecture

```text
User Request
      │
      ▼
Planner
      │
      ▼
Task Classification
      │
      ▼
Content Generation
      │
      ▼
Reflection & Self-Check
      │
      ▼
Revision (if required)
      │
      ▼
DOCX Builder
      │
      ▼
Generated Document
```

---

## Technology Stack

* Python
* FastAPI
* Large Language Models (LLMs)
* Groq API (OpenAI-compatible)
* Pydantic
* python-docx

---

## Project Structure

```text
agentic-docx/
│
├── main.py
├── requirements.txt
├── .env.example
├── README.md
│
├── agent/
│   ├── planner.py
│   ├── orchestrator.py
│   ├── reflection.py
│   ├── doc_builder.py
│   └── llm_client.py
│
└── output/
```

---

## Installation

```bash
git clone https://github.com/<your-username>/agentic-docx.git

cd agentic-docx

pip install -r requirements.txt
```

Create a `.env` file and configure your API key if using an online LLM.

---

## Run the Application

```bash
uvicorn main:app --reload
```

Open the API documentation:

```text
http://127.0.0.1:8000/docs
```

---

## Sample Use Cases

* Meeting Minutes Generator
* Project Proposal Generator
* Business Reports
* Requirement Documents
* Client Documentation
* Internal Technical Documents

---

## Learning Outcomes

This project helped me gain practical experience in:

* Agentic AI workflows
* LLM integration
* Prompt engineering
* AI orchestration
* Reflection-based AI systems
* FastAPI development
* Automated document generation

---

## Future Improvements

* Multi-agent collaboration
* RAG (Retrieval-Augmented Generation)
* Memory support
* PDF generation
* Web interface
* Docker deployment
* Cloud deployment (Azure/AWS)

---

## Author

Personal project developed for learning and demonstrating Agentic AI and LLM application development using Python.
