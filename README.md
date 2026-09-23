# Synora 

**An Autonomous Digital Steward for Goal-Driven and Future-Aware File Management**

Synora (codename **FilePilot**) is an agentic file-management system. Instead of running fixed rules on your files, it takes a plain-language goal ("free up 5GB", "archive anything untouched in 6 months", "find and remove duplicate photos"), reasons about the safest way to do it, and executes the plan through a sandboxed, verifiable controller — reporting back what changed and why.

---

## Why FilePilot

Traditional cleanup tools apply static rules (delete files older than X days, compress folder Y). FilePilot instead:

- **Interprets intent** — turns a natural-language goal into a structured plan
- **Assesses risk before acting** — every file touched is scored before any action is taken
- **Plans and adapts** — drafts a sequence of safe actions, then re-plans if verification shows the goal wasn't met
- **Verifies its own work** — every operation is hash-checked before and after, so nothing is silently corrupted or lost

---

## Architecture

FilePilot is organized into five layers, from UI down to storage.

```
==========================================================================================
1. PRESENTATION LAYER (Frontend)
   Tech: React + Vite
   Components: [ Mission Control ]  |  [ Workspace Dashboard ]  |  [ Audit History ]
==========================================================================================
                                       │
                                       ▼  REST API (JSON)
==========================================================================================
2. API & ROUTING LAYER (Backend Gateway)
   Tech: Python + FastAPI
   Components: [ Endpoints: /mission, /scan, /duplicates ]  |  [ State Management ]
==========================================================================================
                                       │
                                       ▼  Goal & Context
==========================================================================================
3. AGENTIC AI CORE (The Deliberation Engine)
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
4. EXECUTION & PERCEPTION (The Controller)
   Tech: Python Filesystem APIs (os, shutil, hashlib)

   [ SCANNER ] ──────────────> [ EXECUTOR ] ──────────────> [ VERIFIER ]
   Maps workspace,             Runs Sandboxed Actions:      Validates data integrity
   generates SHA-256 hashes    Compress, Quarantine,        (Pre/Post Hash Check)
                               Deduplicate, Restore
==========================================================================================
                                       │
                                       ▼  I/O Operations
==========================================================================================
5. DATA & INFRASTRUCTURE LAYER
   [ Active Files ]      [ Compressed (.gz) ]      [ Quarantine Zone ]      [ Restored ]
==========================================================================================
```

### Layer breakdown

| Layer | Responsibility |
|---|---|
| **1. Presentation** | React + Vite frontend. Mission Control for setting goals, a Workspace Dashboard for live state, and Audit History for reviewing past runs. |
| **2. API & Routing** | FastAPI gateway exposing `/mission`, `/scan`, and `/duplicates`, plus session/state management between frontend and the AI core. |
| **3. Agentic AI Core** | The deliberation engine. A goal interpreter parses natural language into structured JSON, a risk engine scores every candidate file/action, a planner sequences safe operations, and a replanner loops back in if post-execution verification shows the goal wasn't achieved. |
| **4. Execution & Perception** | The controller: a Scanner maps the workspace and hashes files (SHA-256), an Executor runs sandboxed actions (compress, quarantine, deduplicate, restore), and a Verifier re-hashes to confirm integrity pre/post operation. |
| **5. Data & Infrastructure** | Where files actually live day to day — Active Files, Compressed archives (`.gz`), a Quarantine Zone for at-risk items pending review, and Restored files brought back from quarantine or archive. |

---

## Project structure

```
Synora/
├── backend/        # FastAPI gateway + agentic core + execution controller
├── frontend/        # React + Vite client (Mission Control, Dashboard, Audit History)
├── docs/             # Project documentation
├── .env.example      # Environment variable template
└── .gitignore
```

## Safety model

- **Nothing is deleted outright** — risky actions route through quarantine first, with restore available.
- **Every operation is hash-verified** before and after execution.
- **The AI core proposes, the controller disposes** — the planner never touches the filesystem directly; only the sandboxed executor does, against an approved plan.
- **If verification fails**, the replanner is invoked instead of silently giving up or retrying blindly.

---

## Getting started

```bash
git clone https://github.com/PriyaR-2006/Synora.git
cd Synora

# Backend
cd backend
cp ../.env.example .env   # fill in your API keys (Grok/OpenAI, etc.)
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd ../frontend
npm install
npm run dev
```

> Adjust the commands above to match your actual entrypoint/scripts if they differ — this section is a placeholder based on the standard FastAPI + Vite layout and should be updated once the backend/frontend setup steps are finalized.

## Roadmap

- [ ] Expand risk-scoring rules beyond file age/size heuristics
- [ ] Add scheduled/background "future-aware" goals (e.g. recurring cleanup)
- [ ] Multi-workspace support
- [ ] Richer Audit History (diff view per mission)

## Contributing

Issues and PRs are welcome. Please open an issue describing the change before submitting a large PR.

## License

_Add a license (e.g. MIT) — none is currently specified in the repository._
