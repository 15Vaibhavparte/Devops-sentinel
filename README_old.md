# 🚀 DevOps Sentinel  
_Your AI First Responder for DevOps Alerts_

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)  [![FastAPI](https://img.shields.io/badge/fastapi-%5E0.110-green)](https://fastapi.tiangolo.com/)  [![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)  [![Streamlit](https://img.shields.io/badge/streamlit-app-red)](https://streamlit.io/)  [![TiDB Cloud](https://img.shields.io/badge/TiDB-cloud-orange)](https://tidbcloud.com/)  

---

## 📑 Table of Contents
1. [Our Story](#-our-story)  
2. [The Inspiration](#-the-inspiration-from-alert-fatigue-to-ai-first-responder-)  
3. [How We Built It](#-how-we-built-it-a-journey-from-idea-to-autonomous-agent-)  
   - [Foundation (TiDB Cloud)](#1-the-foundation-tidb-cloud)  
   - [Agent’s Brain (RAG Pipeline)](#2-building-the-agents-brain-rag-pipeline)  
   - [UI & Integrations](#3-giving-the-agent-a-voice-ui-and-integrations)  
   - [Portability (Docker)](#4-packaging-for-portability-docker)  
4. [Challenges We Faced](#-challenges-we-faced-)  
5. [What We Learned](#-what-we-learned-)  
6. [Getting Started](#-getting-started)  
7. [Future Vision](#-future-vision)  

---

## 🌟 Our Story
We set out to solve one of the biggest pain points in modern DevOps: **alert fatigue**.  

Instead of engineers drowning in dashboards and logs, we envisioned an **AI First Responder**—an agent that automatically:  
- Intercepts alerts  
- Investigates using runbooks & logs  
- Delivers a clear, actionable solution  

Thus, the **DevOps Sentinel** was born.  

---

## 💡 The Inspiration: From Alert Fatigue to AI First Responder
Modern observability = **alert fatigue** 😫.  

- Engineers are overwhelmed by a flood of alerts  
- Manual investigation leads to burnout and inefficiency  
- Hours of toil → repetitive & demoralizing  

👉 Our solution: **an autonomous agent** that reduces hours of manual work into **minutes**.  

---

## 🚀 How We Built It: A Journey from Idea to Autonomous Agent

### 1. The Foundation (TiDB Cloud)
- Core infrastructure hosted on **TiDB Cloud**  
- Handles both structured log data & unstructured vector embeddings  
- Dedicated `devops_sentinel` database with `knowledgebase` + `logs` tables  

### 2. Building the Agent's Brain (RAG Pipeline)
- **Knowledge Ingestion**  
  - Python script (`ingest.py`) processes DevOps runbooks (Markdown)  
  - Chunking → embeddings via **SentenceTransformer** → stored in **TiDB Vector**  

- **Retrieval & Generation**  
  - **FastAPI backend** embeds queries  
  - Vector similarity search in TiDB retrieves relevant context  
  - Context + query → **Gemini 1.5 Flash LLM** → actionable solution  

### 3. Giving the Agent a Voice (UI and Integrations)
- **Interactive UI**: Streamlit app for Q&A and training  
- **Autonomous Workflow**:  
  - Webhook endpoint `/alert-trigger/` processes simulated **Grafana alerts**  
  - Integrated with **Slack** to auto-post findings

---

### 4. Challenges We Faced
- **Docker Config Issues** → Empty file errors, fixed by careful config validation  
- **API Rate Limiting** → Health check spammed Gemini API; solved via caching (1 call/min)  
- **File Encoding Mismatches** → Runbooks unreadable; fixed with UTF-8 standardization  

---

### 5. What We Learned
- Designing a **modern RAG pipeline**  
- Using **TiDB Vector** for scalable semantic search  
- Prompting & integrating **LLMs (Gemini)**  
- Building both **interactive UIs (Streamlit)** and **robust APIs (FastAPI)**  
- Best practices with **Docker** for reproducibility  

👉 Most importantly → how to **design AI agents** that act, not just answer.  

---

## 🛠 Getting Started

### ✅ Prerequisites
- Python **3.9+**  
- **Docker & Docker Compose**  
- Access to **TiDB Cloud** & **Gemini API**  

### ⚡ Setup

**1. Clone this repo:**  
```bash
git clone https://github.com/your-username/devops-sentinel.git
cd devops-sentinel
```
2. Install dependencies:

```pip install -r requirements.txt```


3. Run locally (dev mode):
```
uvicorn backend.main:app --reload
streamlit run frontend/app.py
```

### 4. Packaging for Portability (Docker):
```
docker-compose up --build
```
- Containerized with `Dockerfile` + `docker-compose.yml`  
- One-command deployment:

## Future Vision
- Expand integrations → Jira, PagerDuty, ServiceNow
- Self-healing capabilities (auto-restart failing services)
- Multi-agent collaboration for complex incidents
- Fine-tuned, domain-specific LLMs

---

## 🏗️ Architecture

```mermaid
flowchart TD
    subgraph User["👩‍💻 DevOps Engineer"]
        UI["Streamlit UI"]
        Slack["Slack Alerts"]
    end

    subgraph Backend["⚡ FastAPI Backend"]
        API["/alert-trigger Webhook"]
        RAG["RAG Pipeline"]
    end

    subgraph DB["🗄️ TiDB Cloud"]
        KB["Knowledgebase (Vector Store)"]
        Logs["Logs Table"]
    end

    subgraph LLM["🤖 Gemini 1.5 Flash LLM"]
        GEN["Solution Generation"]
    end

    %% Connections
    UI -->|Query| API
    Slack -->|Alert Trigger| API
    API --> RAG
    RAG -->|Vector Search| KB
    RAG -->|Context Retrieval| Logs
    RAG --> GEN
    GEN --> API
    API -->|Answer| UI
    API -->|Findings| Slack




