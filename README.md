<div align="center">

# 🧭 Synora — FilePilot

### An Autonomous Digital Steward for Goal-Driven and Future-Aware File Management

*Tell it what you want. It figures out how to get there — safely.*

[![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB?style=for-the-badge&logo=react&logoColor=black)](#)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](#)
[![AI Core](https://img.shields.io/badge/AI%20Core-Grok%20%2F%20OpenAI-8A2BE2?style=for-the-badge)](#)
[![Status](https://img.shields.io/badge/Status-In%20Development-orange?style=for-the-badge)](#)

</div>

---

## ✨ What is FilePilot?

Most cleanup tools are dumb rule-runners: *delete anything older than 90 days*, *zip this folder*. FilePilot is different — it's an **agent**, not a script.

Give it a goal in plain English:

> 🗣️ *"Free up 5GB without touching anything I've opened this month"*
> 🗣️ *"Archive whatever's been untouched for 6+ months"*
> 🗣️ *"Find and clear out duplicate photos"*

...and it **interprets the intent, scores the risk, drafts a plan, executes it inside a sandbox, and verifies every single change** — before reporting back exactly what happened and why.

| 🎯 Goal-driven | 🛡️ Risk-aware | 🔁 Self-correcting | ✅ Verifiable |
|:---:|:---:|:---:|:---:|
| Natural language in, structured plan out | Every file scored before it's touched | Replans automatically if a goal isn't met | SHA-256 hash-checked pre/post every action |

---

## 🏗️ Architecture

FilePilot is built as **five layers**, from the UI you click down to the bytes on disk.

```
==========================================================================================
🖥️  1. PRESENTATION LAYER (Frontend)
   Tech: React + Vite
   Components: [ Mission Control ]  |  [ Workspace Dashboard ]  |  [ Audit History ]
==========================================================================================
                                       │
                                       ▼  REST API (JSON)
==========================================================================================
🔌  2. API & ROUTING LAYER (Backend Gateway)
   Tech: Python + FastAPI
   Components: [ Endpoints: /mission, /scan, /duplicates ]  |  [ State Management ]
==========================================================================================
                                       │
                                       ▼  Goal & Context
==========================================================================================
🧠  3. AGENTIC AI CORE (The Deliberation Engine)
   Tech: Grok (xAI) / OpenAI + Python

   ┌──────────────────────┐      ┌──────────────────────┐      ┌──────────────────────┐
   │ 1. GOAL INTERPRETER  │ ────>│ 2. RISK ENGINE       │ ────>│ 3. PLANNER           │
   │ Translates natural   │      │ Applies safety rules │      │ Drafts sequence of   │
   │ language to JSON     │      │ and scores file risk │      │ safe actions         │
   └──────────────────────┘      └──────────────────────┘      └──────────────────────┘
             ▲                                                            │
             │                   ┌──────────────────────┐                 │
             └───────────────────│ 4. REPLANNER         │<────────────────┘
               (If goal not met) │ Adapts based on      │
                                 │ verification results │
                                 └──────────────────────┘
==========================================================================================
                                       │
                                       ▼  Approved Action Plan
==========================================================================================
⚙️  4. EXECUTION & PERCEPTION (The Controller)
   Tech: Python Filesystem APIs (os, shutil, hashlib)

   [ SCANNER ] ──────────────> [ EXECUTOR ] ──────────────> [ VERIFIER ]
   Maps workspace,             Runs Sandboxed Actions:      Validates data integrity
   generates SHA-256 hashes    Compress, Quarantine,        (Pre/Post Hash Check)
                               Deduplicate, Restore
==========================================================================================
                                       │
                                       ▼  I/O Operations
==========================================================================================
🗄️  5. DATA & INFRASTRUCTURE LAYER
   [ Active Files ]      [ Compressed (.gz) ]      [ Quarantine Zone ]      [ Restored ]
==========================================================================================
```

### 🔍 Layer by layer

| Layer | What it does |
|---|---|
| 🖥️ **1. Presentation** | React + Vite frontend — Mission Control for setting goals, a live Workspace Dashboard, and Audit History for past runs. |
| 🔌 **2. API & Routing** | FastAPI gateway exposing `/mission`, `/scan`, `/duplicates`, plus session/state handling between UI and AI core. |
| 🧠 **3. Agentic AI Core** | The brains: goal interpreter → risk engine → planner, with a replanner that loops back in if verification says the goal wasn't met. |
| ⚙️ **4. Execution & Perception** | The hands: Scanner maps and hashes the workspace, Executor runs sandboxed actions, Verifier re-hashes to confirm nothing broke. |
| 🗄️ **5. Data & Infrastructure** | Where files live — Active, Compressed (`.gz`), Quarantine (pending review), and Restored. |

---

## 📁 Project structure

```
Synora/
├── backend/        🔌 FastAPI gateway + agentic core + execution controller
├── frontend/        🖥️ React + Vite client (Mission Control, Dashboard, Audit History)
├── docs/             📚 Project documentation
├── .env.example      🔑 Environment variable template
└── .gitignore
```

## 🛡️ Safety model

> Autonomy is only useful if you can trust it. FilePilot is built paranoid by default.

- 🚫 **Nothing is deleted outright** — risky actions route through quarantine first, with restore available
- 🔐 **Every operation is hash-verified** (SHA-256) before *and* after execution
- 🤝 **The AI proposes, the controller disposes** — the planner never touches the filesystem directly; only the sandboxed executor does, against an approved plan
- 🔁 **If verification fails**, the replanner kicks in instead of silently giving up or blindly retrying

---

## 🚀 Getting started

```bash
git clone https://github.com/PriyaR-2006/Synora.git
cd Synora

# 🔌 Backend
cd backend
cp ../.env.example .env   # fill in your API keys (Grok/OpenAI, etc.)
pip install -r requirements.txt
uvicorn main:app --reload

# 🖥️ Frontend
cd ../frontend
npm install
npm run dev
```

> ⚠️ These commands are a best-guess placeholder based on the standard FastAPI + Vite layout — swap in the real entrypoint/scripts once they're finalized.

---

## 🗺️ Roadmap

- [ ] Expand risk-scoring beyond file age/size heuristics
- [ ] "Future-aware" scheduled/recurring goals
- [ ] Multi-workspace support
- [ ] Richer Audit History (diff view per mission)

## 🤝 Contributing

Issues and PRs are welcome — open an issue describing the change before submitting a large PR.

## 📄 License

_No license specified yet — add one (MIT is a solid default) before accepting outside contributions._

---


