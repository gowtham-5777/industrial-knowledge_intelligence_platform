# Industrial Brain AI — Implementation Plan Report

**Document Type:** Master Execution Guide / Engineering Roadmap  
**Product:** Industrial Brain AI  
**Classification:** Implementation Planning, Milestone Management, Progress Tracking  
**Status:** Active — Single Source of Truth for Development  
**Architecture Authority:** [ARCHITECTURE.md](ARCHITECTURE.md) — Master Software Architecture Report (finalized; **never modify unless explicitly requested**)  
**Created:** 2026-07-16  
**Last Updated:** 2026-07-17  

---

### Document Purpose

This file is the **master execution guide** for Industrial Brain AI. It converts the finalized Architecture Report into an executable engineering roadmap.

| This document IS | This document is NOT |
|---|---|
| Implementation planning | A second architecture document |
| Milestone & task tracking | A redesign of modules or tech |
| Progress & dependency management | A place to invent new features |
| Definition of Done + validation | A substitute for the Architecture Report |

**Rule:** If this plan and the Architecture Report ever appear to conflict, **the Architecture Report wins**. Update this plan to re-align; never silently drift.

---

### Active Execution Cursor (Update on Every Implementation Prompt)

| Field | Value |
|---|---|
| **Current Phase** | Phase 1 — Foundation |
| **Current Milestone** | Milestone 1.11 — Foundation Validation Gate |
| **Current Task** | Not Started |
| **Current Subtask** | — |
| **Overall Progress** | ~18% (10 milestones complete) |
| **Active Owner** | Cursor Agent / Engineering Team |
| **Blocked By** | — |
| **Next Milestone After Current** | Phase 2 — Document Intelligence (after 1.11 gate) |
| **Last Tracker Update** | 2026-07-20 — Milestone 1.10 Complete; awaiting approval for 1.11 |

> **Cursor obligation:** Before implementing anything, read this section, locate the active milestone, implement only that scope, validate, update this tracker, then stop.

---

# 1. Project Overview

## 1.1 Project Vision

Build an **AI-powered Industrial Knowledge Intelligence Platform** — an Industrial Digital Brain that transforms disconnected engineering documentation into continuously evolving, explainable operational intelligence.

Users explore **industrial assets**, receive **knowledge**, interact with **AI**, and make better **decisions**.

## 1.2 Project Goal

Deliver a production-bound modular monolith (hackathon = Version 1) that:

1. Discovers and catalogs a multi-domain industrial corpus (~27,300 documents) from Google Drive  
2. Continuously indexes knowledge with Adaptive Prioritization  
3. Centers UX on **Asset 360** (Motors as hackathon hero)  
4. Provides explainable health scores, AI summaries, recommendations, and an Industrial Copilot with citations  
5. Remains asset-agnostic so pumps, valves, compressors, boilers, turbines, pipelines, chemical plants, and oil refineries work without redesign  

## 1.3 Target Problem Statement

Industrial engineers manage tens of thousands of engineering documents across drawings, datasheets, test reports, manuals, safety procedures, regulations, certifications, sensors, and SOPs. Finding the right evidence for one asset takes hours. Knowledge is fragmented across folders, formats, and systems.

**Industrial Brain AI** collapses that fragmentation into an asset-first intelligence experience.

## 1.4 Hackathon Goal (Version 1 — Jul 16–19, 2026)

| Objective | Success Criteria |
|---|---|
| Scale narrative | Catalog ≈27,300 docs; show live Continuous Intelligent Indexing |
| Hero demo | One fully indexed **Motor Asset 360** end-to-end |
| Intelligence | AI Summary + Explainable Health Score + Recommendations + Copilot with citations |
| Differentiator | Drawing-number cross-reference graph spine |
| Enterprise feel | Asset-first UX — never “chat with PDF” |

**Compressed calendar (Architecture §24 overlay):**

| Day | Phases | Critical Path |
|---|---|---|
| Day 1 | Phase 1 + start Phase 2 | Discovery, asset registry, fleet dashboard |
| Day 2 | Finish Phase 2 + Phase 3 | Hero Motor Asset 360 complete |
| Day 3 | Phase 4 core + Phase 5 minimum + Phase 6 | Copilot, compliance, RBAC lite, demo polish |

## 1.5 Production Goal

Evolve the same modular monolith into an on-prem / hybrid enterprise platform:

- Customer blob / SharePoint / NAS connectors (replacing Google Drive as primary source)  
- Docling + PaddleOCR primary parsing; bge-m3 embeddings; vLLM + Llama on-prem  
- OIDC/SAML IdP, full RBAC, immutable audit, observability  
- Multi-site, multi-asset-type Asset 360 depth  

## 1.6 North Star

> **Assets are the application. Documents are evidence. Knowledge is the product. AI is the interface.**

**Primary workflow:** Asset → Knowledge → AI → Decision

## 1.7 Expected Final Product

| Layer | Deliverable |
|---|---|
| Backend | FastAPI modular monolith + Celery/Redis workers |
| Frontend | Next.js App Router enterprise web app |
| Data | PostgreSQL (SoR) + Neo4j (derived graph) + Qdrant (semantic index) + object storage |
| Intelligence | Agentic Hybrid Graph RAG via LangGraph |
| Flagship UX | Asset 360 (Motor specialization for demo) |
| Ops | Docker Compose local; hybrid cloud demo path |

## 1.8 One-Page Executive Summary

Industrial Brain AI is an asset-agnostic Industrial Knowledge Intelligence Platform. Over a real multi-domain corpus (~27,300 engineering documents on Google Drive; Motors 20,134 as the richest hero domain), the system discovers documents, continuously indexes them with Adaptive Prioritization, builds a motor-centric knowledge graph (drawing-number spine), and surfaces explainable operational intelligence through Asset Explorer, Asset 360, Timeline, AI Summary, Health Score, Recommendations, Knowledge Graph, Compliance, Maintenance Intelligence, and Industrial Copilot.

Technically it is a **Modular Monolith**: FastAPI + Next.js + PostgreSQL + Neo4j + Qdrant + Redis/Celery + LangGraph + Azure Document Intelligence (hackathon) with a credible on-prem path. Business rules (health, compliance, scoring) live in Python services — never in LLM prompts. Hackathon Version 1 proves one complete Motor Asset 360 digital twin journey; architecture already supports every other industrial asset type without redesign.

---

# 2. Development Principles

These rules are **binding** for every implementation prompt. They align with Architecture §23 Engineering Governance.

## 2.1 Phase Discipline

1. **Never skip phases.** Foundation → Document Intelligence → Asset Intelligence → Industrial AI → Enterprise → Polish.  
2. **Never jump milestones** inside a phase unless the active milestone is Complete.  
3. **Never implement future milestones** “while we’re here.”  
4. **Never build UI before backend foundations** for that capability.  
5. **Never build AI before data exists** for that capability.  
6. **Never build dashboards before intelligence exists** for that capability.  

## 2.2 Architecture Fidelity

7. **Do not redesign the architecture.**  
8. **Do not change technologies** listed in Architecture §21.  
9. **Do not invent new modules** outside Architecture’s recommended module set.  
10. **Do not contradict** persistence hierarchy: PostgreSQL = SoR; Neo4j/Qdrant = derived.  
11. Prefer **extension over duplication**; reuse services, repositories, schemas.  

## 2.3 Codebase Hygiene

12. **Never create unnecessary files or folders.**  
13. **Never duplicate** business logic, models, schemas, repositories, services, APIs, or utilities.  
14. Prefer **fewer high-quality files** (300–500 lines acceptable) over many tiny files.  
15. No `helpers.py` / `utils.py` / `misc.py` / `common.py` / `shared.py` dumping grounds without architectural justification.  
16. No placeholder / stub implementations unless explicitly marked `PLACEHOLDER:` with owner + follow-up milestone.  
17. No God classes, God services, or God files.  

## 2.4 Quality Bars

18. Follow **modular monolith** boundaries (Architecture §9, §23).  
19. Every feature must have **validation**.  
20. Every API must have **typed schemas** (Pydantic / Zod as applicable).  
21. Every module must remain **independently understandable**.  
22. All code must be **production quality** — hackathon is V1 of production, not a throwaway demo.  
23. Every commit must leave the project **runnable**.  
24. **Document every assumption** in this plan’s Assumptions Log when discovered.  
25. **Never hardcode** secrets, URLs, model names as magic strings in business logic — use configuration / environment variables.  
26. **Never use `print()`** — structured logging only.  
27. Routes only: Validate → Call Services → Return Response.  
28. LLMs own reasoning/narration; **Python services own deterministic scores and compliance logic**.  

## 2.5 Product Language Rules (UI)

| Use on screen | Never use on screen |
|---|---|
| Industrial Digital Brain | RAG |
| Knowledge Intelligence | Vector database / embeddings |
| Continuous Intelligent Indexing | Wave 1 / Wave 2 |
| Adaptive Prioritization | “Only N reports parsed” |
| Asset 360 / Motor 360 | Document upload demo framing |
| Explainable Health Score | ML prediction |

---

# 3. Development Workflow

```
Architecture Report (immutable authority)
        ↓
Phase (sequential — never skip)
        ↓
Milestone (one active at a time)
        ↓
Task (one primary in-progress task)
        ↓
Subtask
        ↓
Implementation (scoped only to active task)
        ↓
Validation Checklist (manual + automated)
        ↓
Testing (unit / API / integration as required by milestone DoD)
        ↓
Update Progress Tracker in this document
        ↓
Mark Task → Milestone Complete
        ↓
STOP — suggest next milestone; do not auto-continue
```

## 3.1 Cursor Execution Loop (Mandatory)

On every user implementation request:

1. **Read** `docs/IMPLEMENTATION_PLAN.md` (this file) and confirm Architecture alignment  
2. **Identify** Current Phase / Milestone / Task  
3. **Check** Depends On / Blocked By  
4. **Mark** task In Progress in Progress Tracker  
5. **Implement** only that scope  
6. **Validate** against Definition of Done + Validation Checklist  
7. **List** files created/modified and why each exists  
8. **Update** tracker (status, notes, completion date)  
9. **Suggest** next task/milestone  
10. **Stop** — do not auto-advance into the next milestone  

## 3.2 Hard Prohibitions

- Cursor must **NEVER** jump between phases  
- Cursor must **NEVER** implement Milestone N+1 while Milestone N is incomplete  
- Cursor must **NEVER** “also quickly add” Enterprise/AI features during Foundation  
- Cursor must **NEVER** modify the Architecture Report unless the user explicitly requests it  

---

# 4. Project Roadmap

Phases match Architecture §24 exactly.

## Phase 1 — Foundation

| Field | Content |
|---|---|
| **Purpose** | Production-ready backend + frontend shell + data ingress foundation |
| **Expected Deliverables** | Project scaffold, config, auth, PostgreSQL, Docker, logging, Google Drive connector, document catalog/upload/storage, basic frontend shell |
| **Dependencies** | Architecture Report finalized; env secrets available (or `.env.example` defined) |
| **Completion Criteria** | App boots via Docker Compose; health endpoints live; auth works; Drive discovery can catalog documents; frontend shell navigates; logs structured |
| **Estimated Complexity** | High (breadth) — Medium per milestone |
| **Hackathon Day** | Day 1 (primary) |

## Phase 2 — Document Intelligence

| Field | Content |
|---|---|
| **Purpose** | Transform documents into structured, retrievable knowledge |
| **Expected Deliverables** | OCR/parsing, metadata + entity extraction, chunking, embeddings, Qdrant, Neo4j graph sync, hybrid retrieval, citations, Continuous Intelligent Indexing workers |
| **Dependencies** | Phase 1 Complete |
| **Completion Criteria** | Priority docs for hero motor parsed → chunked → embedded → graph-linked; hybrid retrieval returns cited evidence |
| **Estimated Complexity** | Very High |
| **Hackathon Day** | Day 1 PM → Day 2 AM |

## Phase 3 — Asset Intelligence

| Field | Content |
|---|---|
| **Purpose** | Build the Industrial Asset Brain (flagship product experience) |
| **Expected Deliverables** | Asset registry, Asset Explorer, Asset 360 (Motor hero), Timeline, AI Summary, Related Assets, Drawing relationships, Search, Recommendations, Health Score, Graph UI, Fleet Dashboard |
| **Dependencies** | Phase 2 Complete (enough indexed knowledge for hero motor) |
| **Completion Criteria** | Hero Motor Asset 360 fully populated end-to-end for demo |
| **Estimated Complexity** | Very High (product-critical) |
| **Hackathon Day** | Day 2 |

## Phase 4 — Industrial AI

| Field | Content |
|---|---|
| **Purpose** | Operational intelligence layer |
| **Expected Deliverables** | Query router, Industrial Copilot, Maintenance Intelligence, RCA (test-anomaly), Compliance Intelligence, Analytics, cross-document reasoning |
| **Dependencies** | Phase 3 Complete (Asset 360 context + retrieval) |
| **Completion Criteria** | Motor-scoped Copilot answers with citations; maintenance/compliance/RCA screens work on hero motor |
| **Estimated Complexity** | High |
| **Hackathon Day** | Day 3 AM |

## Phase 5 — Enterprise

| Field | Content |
|---|---|
| **Purpose** | Production readiness hardening |
| **Expected Deliverables** | RBAC, audit logs, caching, worker hardening, monitoring/observability, security hardening |
| **Dependencies** | Phase 4 core Complete (minimum viable AI surfaces) |
| **Completion Criteria** | Role-gated access; audit events recorded; critical paths cached/monitored; security baseline met |
| **Estimated Complexity** | Medium–High |
| **Hackathon Day** | Day 3 (minimum viable subset) |

## Phase 6 — Testing & Polish

| Field | Content |
|---|---|
| **Purpose** | Hackathon-ready, demo-reliable release |
| **Expected Deliverables** | Tests, golden eval (100+ Qs target; hackathon minimum viable golden set), deploy, demo video, presentation, docs, performance tuning, bug fixes |
| **Dependencies** | Phases 1–5 minimum viable Complete |
| **Completion Criteria** | Smoke + golden path pass; demo rehearsed; backup video ready; deployment stable |
| **Estimated Complexity** | Medium |
| **Hackathon Day** | Day 3 PM + Jul 19 buffer |

---

# 5. Milestone Breakdown

## Phase 1 — Foundation

| ID | Milestone | Status |
|---|---|---|
| 1.1 | Project Bootstrap | Complete |
| 1.2 | Backend Foundation | Complete |
| 1.3 | Database (PostgreSQL) | Complete |
| 1.4 | Authentication | Complete |
| 1.5 | Object Storage | Complete |
| 1.6 | Google Drive Integration | Complete |
| 1.7 | Document Catalog & Upload | Complete |
| 1.8 | Frontend Shell | Complete |
| 1.9 | Docker Compose Stack | Complete |
| 1.10 | Logging & Observability Foundation | Complete |
| 1.11 | Foundation Validation Gate | Not Started |

## Phase 2 — Document Intelligence

| ID | Milestone | Status |
|---|---|---|
| 2.1 | Parsing & OCR Pipeline | Not Started |
| 2.2 | Metadata & Entity Extraction | Not Started |
| 2.3 | Chunking | Not Started |
| 2.4 | Embedding Pipeline | Not Started |
| 2.5 | Qdrant Vector Indexing | Not Started |
| 2.6 | Neo4j Knowledge Graph Sync | Not Started |
| 2.7 | Hybrid Retrieval Engine | Not Started |
| 2.8 | Citation & Provenance Pipeline | Not Started |
| 2.9 | Continuous Intelligent Indexing Workers | Not Started |
| 2.10 | Document Intelligence Validation Gate | Not Started |

## Phase 3 — Asset Intelligence

| ID | Milestone | Status |
|---|---|---|
| 3.1 | Asset Registry (Asset-Agnostic + Motor Hierarchy) | Not Started |
| 3.2 | Asset Explorer | Not Started |
| 3.3 | Asset 360 Aggregation API | Not Started |
| 3.4 | Asset Timeline | Not Started |
| 3.5 | AI Asset Summary Service | Not Started |
| 3.6 | Explainable Health / Risk Score Engine | Not Started |
| 3.7 | AI Recommendation Engine | Not Started |
| 3.8 | Drawing Explorer & Cross-Reference | Not Started |
| 3.9 | Knowledge Graph UI | Not Started |
| 3.10 | Unified Search | Not Started |
| 3.11 | Fleet Dashboard & Indexing Status UI | Not Started |
| 3.12 | Asset 360 Frontend Flagship | Not Started |
| 3.13 | Asset Intelligence Validation Gate | Not Started |

## Phase 4 — Industrial AI

| ID | Milestone | Status |
|---|---|---|
| 4.1 | Query Router | Not Started |
| 4.2 | Industrial Copilot (LangGraph) | Not Started |
| 4.3 | Maintenance Intelligence | Not Started |
| 4.4 | Test Anomaly RCA Assistant | Not Started |
| 4.5 | Compliance Intelligence Center | Not Started |
| 4.6 | Analytics | Not Started |
| 4.7 | Cross-Document Reasoning Hardening | Not Started |
| 4.8 | Industrial AI Validation Gate | Not Started |

## Phase 5 — Enterprise

| ID | Milestone | Status |
|---|---|---|
| 5.1 | RBAC Hardening | Not Started |
| 5.2 | Audit Logs | Not Started |
| 5.3 | Caching Strategy | Not Started |
| 5.4 | Background Worker Hardening | Not Started |
| 5.5 | Monitoring & Observability | Not Started |
| 5.6 | Security Hardening | Not Started |
| 5.7 | Enterprise Validation Gate | Not Started |

## Phase 6 — Testing & Polish

| ID | Milestone | Status |
|---|---|---|
| 6.1 | Automated Test Suite Expansion | Not Started |
| 6.2 | Golden Evaluation Dataset | Not Started |
| 6.3 | E2E & Demo Reliability Gates | Not Started |
| 6.4 | Bug Fix & UX Polish | Not Started |
| 6.5 | Deployment | Not Started |
| 6.6 | Demo Video, Presentation & Architecture Slides | Not Started |
| 6.7 | Documentation Sync | Not Started |
| 6.8 | Final Release Validation Gate | Not Started |

---

# 6. Task Breakdown

Tasks below are the executable units. Status values: `Not Started` | `In Progress` | `Blocked` | `Complete`.

---

## Milestone 1.1 — Project Bootstrap

| Task ID | Task | Status |
|---|---|---|
| 1.1.1 | Create monorepo / workspace layout | Complete |
| 1.1.2 | Initialize backend Python project | Complete |
| 1.1.3 | Initialize frontend Next.js TypeScript app | Complete |
| 1.1.4 | Add root README, `.env.example`, `.gitignore` | Complete |
| 1.1.5 | Define package/tooling baselines (lint, format, pytest, ESLint) | Complete |

## Milestone 1.2 — Backend Foundation

| Task ID | Task | Status |
|---|---|---|
| 1.2.1 | Initialize FastAPI application entrypoint | Complete |
| 1.2.2 | Project settings via pydantic-settings / env | Complete |
| 1.2.3 | Dependency injection container / FastAPI Depends pattern | Complete |
| 1.2.4 | Middleware stack (CORS, request ID, timing) | Complete |
| 1.2.5 | API versioning (`/api/v1`) | Complete |
| 1.2.6 | Global error handling + error envelope | Complete |
| 1.2.7 | OpenAPI configuration | Complete |
| 1.2.8 | Health / readiness endpoints | Complete |
| 1.2.9 | Response envelope convention `{ data, meta, errors }` | Complete |

## Milestone 1.3 — Database (PostgreSQL)

| Task ID | Task | Status |
|---|---|---|
| 1.3.1 | SQLAlchemy / Alembic setup | Complete |
| 1.3.2 | Core system tables (`users`, `roles`, `audit_events` stubs as needed) | Complete |
| 1.3.3 | Asset-agnostic registry tables + motor specialization tables | Complete |
| 1.3.4 | Document catalog / documents / versions tables | Complete |
| 1.3.5 | Drawing numbers + link tables | Complete |
| 1.3.6 | Indexing job / gdrive sync state tables | Complete |
| 1.3.7 | Initial migration + seed script hooks | Complete |
| 1.3.8 | Repository base pattern | Complete |

## Milestone 1.4 — Authentication

| Task ID | Task | Status |
|---|---|---|
| 1.4.1 | Auth provider choice implementation (Clerk/Auth0 **or** JWT seed users) | Complete |
| 1.4.2 | Login / refresh / me endpoints | Complete |
| 1.4.3 | Auth middleware protecting `/api/v1` | Complete |
| 1.4.4 | Seed roles (PlantOperator … SystemAdmin) | Complete |
| 1.4.5 | Frontend auth session wiring | Complete |

## Milestone 1.5 — Object Storage

| Task ID | Task | Status |
|---|---|---|
| 1.5.1 | Storage abstraction (Azure Blob / MinIO-compatible) | Complete |
| 1.5.2 | Upload / download / signed URL operations | Complete |
| 1.5.3 | MIME + size validation | Complete |
| 1.5.4 | Wire storage settings via env | Complete |

## Milestone 1.6 — Google Drive Integration

| Task ID | Task | Status |
|---|---|---|
| 1.6.1 | Drive auth (service account or OAuth shared folder) | Complete |
| 1.6.2 | Discovery pass (`files.list` pagination) | Complete |
| 1.6.3 | Preserve folder path metadata | Complete |
| 1.6.4 | Idempotency via `drive_file_id` + `md5Checksum` | Complete |
| 1.6.5 | Checkpoint / resume state | Complete |
| 1.6.6 | Selective stream download to object storage | Complete |
| 1.6.7 | Sync status API | Complete |

## Milestone 1.7 — Document Catalog & Upload

| Task ID | Task | Status |
|---|---|---|
| 1.7.1 | Catalog upsert from Drive discovery | Complete |
| 1.7.2 | Manual upload API (PDF/DOCX/XLSX/images) | Complete |
| 1.7.3 | Document list/get endpoints (secondary UX support) | Complete |
| 1.7.4 | Doc category/subtype classification from path | Complete |
| 1.7.5 | Asset stub linking from filenames/drawing numbers (skeleton) | Complete |

## Milestone 1.8 — Frontend Shell

| Task ID | Task | Status |
|---|---|---|
| 1.8.1 | Next.js App Router + Tailwind + shadcn/ui baseline | Complete |
| 1.8.2 | Enterprise sidebar navigation (Architecture §10 routes) | Complete |
| 1.8.3 | App layout, theme tokens, dark/light support | Complete |
| 1.8.4 | API client + TanStack Query setup | Complete |
| 1.8.5 | Placeholder pages for primary nav items (no fake business logic) | Complete |
| 1.8.6 | Auth-gated app shell | Complete |

## Milestone 1.9 — Docker Compose Stack

| Task ID | Task | Status |
|---|---|---|
| 1.9.1 | Dockerfile for API | Complete |
| 1.9.2 | Dockerfile for frontend (dev + prod targets as needed) | Complete |
| 1.9.3 | Compose services: api, web, postgres, redis, minio/blob emulator, neo4j, qdrant | Complete |
| 1.9.4 | Volume + network configuration | Complete |
| 1.9.5 | One-command local boot documentation in README | Complete |

## Milestone 1.10 — Logging & Observability Foundation

| Task ID | Task | Status |
|---|---|---|
| 1.10.1 | Structured JSON logging | Complete |
| 1.10.2 | Request correlation IDs | Complete |
| 1.10.3 | Module logger conventions | Complete |
| 1.10.4 | Basic metrics hooks (request latency counters) | Complete |

## Milestone 1.11 — Foundation Validation Gate

| Task ID | Task | Status |
|---|---|---|
| 1.11.1 | Run full Phase 1 validation checklist | Not Started |
| 1.11.2 | Fix blocking defects | Not Started |
| 1.11.3 | Mark Phase 1 Complete in tracker | Not Started |

---

## Milestone 2.1 — Parsing & OCR Pipeline

| Task ID | Task | Status |
|---|---|---|
| 2.1.1 | Parser router by MIME / folder tier (T0–T4) | Not Started |
| 2.1.2 | PyMuPDF + pdfplumber handlers | Not Started |
| 2.1.3 | Azure Document Intelligence layout handler | Not Started |
| 2.1.4 | Native XML/CSV/HTML handlers for regulations | Not Started |
| 2.1.5 | Metadata-only path for CAD/3D | Not Started |
| 2.1.6 | Parse job state machine integration | Not Started |

## Milestone 2.2 — Metadata & Entity Extraction

| Task ID | Task | Status |
|---|---|---|
| 2.2.1 | Drawing number regex extractor (`3GZF`, `9AKK`, `A1/A2/A3`) | Not Started |
| 2.2.2 | Motor type / frame / power field extractors | Not Started |
| 2.2.3 | IEC 60034 test measurement extraction | Not Started |
| 2.2.4 | Certification / regulation field extractors | Not Started |
| 2.2.5 | Extraction candidate + review queue persistence | Not Started |

## Milestone 2.3 — Chunking

| Task ID | Task | Status |
|---|---|---|
| 2.3.1 | Doc-type-aware chunkers (tests, datasheets, manuals, regulations, drawings) | Not Started |
| 2.3.2 | Chunk metadata payload contract | Not Started |
| 2.3.3 | Parent section retention for citations | Not Started |
| 2.3.4 | Persist `document_chunks` | Not Started |

## Milestone 2.4 — Embedding Pipeline

| Task ID | Task | Status |
|---|---|---|
| 2.4.1 | Embedding provider abstraction | Not Started |
| 2.4.2 | Hackathon provider (`text-embedding-3-small` or `voyage-3`) | Not Started |
| 2.4.3 | Store `embedding_model_version` | Not Started |
| 2.4.4 | Batch + incremental embed jobs | Not Started |

## Milestone 2.5 — Qdrant Vector Indexing

| Task ID | Task | Status |
|---|---|---|
| 2.5.1 | Collection schema + payload indexes | Not Started |
| 2.5.2 | Upsert / delete / reindex operations | Not Started |
| 2.5.3 | Hybrid dense (+ sparse if enabled) configuration | Not Started |
| 2.5.4 | Filter by asset/doc_type/drawing_number | Not Started |

## Milestone 2.6 — Neo4j Knowledge Graph Sync

| Task ID | Task | Status |
|---|---|---|
| 2.6.1 | Graph schema constraints/indexes | Not Started |
| 2.6.2 | Asset/Motor center-node projection | Not Started |
| 2.6.3 | DrawingNumber linker hubs | Not Started |
| 2.6.4 | HAS_* relationship writers from SoR | Not Started |
| 2.6.5 | Idempotent graph sync jobs | Not Started |

## Milestone 2.7 — Hybrid Retrieval Engine

| Task ID | Task | Status |
|---|---|---|
| 2.7.1 | Parallel vector + keyword/metadata + graph expansion | Not Started |
| 2.7.2 | Reciprocal Rank Fusion | Not Started |
| 2.7.3 | Parent document promotion | Not Started |
| 2.7.4 | Reranker integration | Not Started |
| 2.7.5 | Structured context assembler | Not Started |

## Milestone 2.8 — Citation & Provenance Pipeline

| Task ID | Task | Status |
|---|---|---|
| 2.8.1 | Citation formatter `[doc_id:chunk_id]` | Not Started |
| 2.8.2 | Citation resolver / verification | Not Started |
| 2.8.3 | Retrieval trace persistence | Not Started |
| 2.8.4 | Confidence scoring inputs | Not Started |

## Milestone 2.9 — Continuous Intelligent Indexing Workers

| Task ID | Task | Status |
|---|---|---|
| 2.9.1 | Celery/ARQ worker bootstrap | Not Started |
| 2.9.2 | Adaptive priority queue (test reports → … → drawings) | Not Started |
| 2.9.3 | Job states: queued→parsing→extracting→indexing→graph_sync→ready|failed | Not Started |
| 2.9.4 | Indexing status APIs for UI | Not Started |
| 2.9.5 | Hero motor + priority subset selection tooling | Not Started |

## Milestone 2.10 — Document Intelligence Validation Gate

| Task ID | Task | Status |
|---|---|---|
| 2.10.1 | Validate hero motor evidence chain exists | Not Started |
| 2.10.2 | Run Phase 2 checklists | Not Started |
| 2.10.3 | Mark Phase 2 Complete | Not Started |

---

## Milestone 3.1 — Asset Registry

| Task ID | Task | Status |
|---|---|---|
| 3.1.1 | AssetType discriminator model + APIs | Not Started |
| 3.1.2 | Motor hierarchy: ProductLine → Family → Model → Unit | Not Started |
| 3.1.3 | Alias table for lookup | Not Started |
| 3.1.4 | Catalog-driven asset stub enrichment | Not Started |
| 3.1.5 | Select/confirm hero motor + 4 supporting motors | Not Started |

## Milestone 3.2 — Asset Explorer

| Task ID | Task | Status |
|---|---|---|
| 3.2.1 | List/search/filter motors API | Not Started |
| 3.2.2 | Explorer UI (browse by frame/power/IE) | Not Started |
| 3.2.3 | Open Asset 360 navigation | Not Started |

## Milestone 3.3 — Asset 360 Aggregation API

| Task ID | Task | Status |
|---|---|---|
| 3.3.1 | Single-bundle endpoint (specs, docs, summary, health, recs, timeline, subgraph) | Not Started |
| 3.3.2 | Document panels grouping by category | Not Started |
| 3.3.3 | Related assets query | Not Started |

## Milestone 3.4 — Asset Timeline

| Task ID | Task | Status |
|---|---|---|
| 3.4.1 | Timeline event builder from metadata/extracted dates | Not Started |
| 3.4.2 | Timeline API | Not Started |
| 3.4.3 | Estimated-date honest UX badge support | Not Started |

## Milestone 3.5 — AI Asset Summary Service

| Task ID | Task | Status |
|---|---|---|
| 3.5.1 | Structured summary schema | Not Started |
| 3.5.2 | Scoped retrieval + LLM structured generation | Not Started |
| 3.5.3 | Cache table + invalidation on new links | Not Started |
| 3.5.4 | “Not available in indexed knowledge” honesty rules | Not Started |

## Milestone 3.6 — Explainable Health / Risk Score Engine

| Task ID | Task | Status |
|---|---|---|
| 3.6.1 | Deterministic weighted scoring (Python only) | Not Started |
| 3.6.2 | Evidence records for each bullet | Not Started |
| 3.6.3 | Recompute triggers | Not Started |
| 3.6.4 | API: score + reasoning bullets | Not Started |

## Milestone 3.7 — AI Recommendation Engine

| Task ID | Task | Status |
|---|---|---|
| 3.7.1 | Recommendation templates + LangGraph sub-agent | Not Started |
| 3.7.2 | Cache + refresh API | Not Started |
| 3.7.3 | Citation-backed recommendation cards contract | Not Started |

## Milestone 3.8 — Drawing Explorer & Cross-Reference

| Task ID | Task | Status |
|---|---|---|
| 3.8.1 | Drawing number lookup API | Not Started |
| 3.8.2 | Cross-reference bundle API | Not Started |
| 3.8.3 | Drawing Explorer UI | Not Started |

## Milestone 3.9 — Knowledge Graph UI

| Task ID | Task | Status |
|---|---|---|
| 3.9.1 | Motor-centered subgraph API | Not Started |
| 3.9.2 | Graph visualization (React Flow or vis-network) | Not Started |
| 3.9.3 | Mini-graph embed for Asset 360 | Not Started |

## Milestone 3.10 — Unified Search

| Task ID | Task | Status |
|---|---|---|
| 3.10.1 | Unified search API (motor + knowledge + drawing) | Not Started |
| 3.10.2 | Search UI page | Not Started |

## Milestone 3.11 — Fleet Dashboard & Indexing Status UI

| Task ID | Task | Status |
|---|---|---|
| 3.11.1 | Dashboard KPI API | Not Started |
| 3.11.2 | Continuous Indexing progress UI | Not Started |
| 3.11.3 | Fleet dashboard page | Not Started |

## Milestone 3.12 — Asset 360 Frontend Flagship

| Task ID | Task | Status |
|---|---|---|
| 3.12.1 | Asset 360 page layout (Architecture wireframe) | Not Started |
| 3.12.2 | Header, summary, health, recommendations zones | Not Started |
| 3.12.3 | Tabs: Timeline, Documents, Tests, Drawings, Compliance, Graph | Not Started |
| 3.12.4 | Embedded Copilot entry point (context handoff; agent may land in Phase 4) | Not Started |
| 3.12.5 | Hero motor end-to-end population verification | Not Started |

## Milestone 3.13 — Asset Intelligence Validation Gate

| Task ID | Task | Status |
|---|---|---|
| 3.13.1 | Run Phase 3 checklists on hero motor | Not Started |
| 3.13.2 | Mark Phase 3 Complete | Not Started |

---

## Milestone 4.1 — Query Router

| Task ID | Task | Status |
|---|---|---|
| 4.1.1 | Intent classification (MotorLookup, TestReportHistory, Procedure, RCA, Compliance, DrawingCrossRef, OpenDomain) | Not Started |
| 4.1.2 | Entity linking (model/serial/drawing) | Not Started |
| 4.1.3 | Fast-model routing (Gemini Flash or equivalent) | Not Started |

## Milestone 4.2 — Industrial Copilot

| Task ID | Task | Status |
|---|---|---|
| 4.2.1 | LangGraph agent graph | Not Started |
| 4.2.2 | Shared tools (`get_motor_360`, timeline, tests, compliance, search, graph) | Not Started |
| 4.2.3 | SSE streaming chat API | Not Started |
| 4.2.4 | Motor-scoped context when launched from Asset 360 | Not Started |
| 4.2.5 | Copilot UI (global + embedded) | Not Started |
| 4.2.6 | Feedback capture | Not Started |

## Milestone 4.3 — Maintenance Intelligence

| Task ID | Task | Status |
|---|---|---|
| 4.3.1 | Test metric trends service | Not Started |
| 4.3.2 | Anomaly pattern detection (rule-assisted) | Not Started |
| 4.3.3 | Maintenance Intelligence UI | Not Started |

## Milestone 4.4 — Test Anomaly RCA Assistant

| Task ID | Task | Status |
|---|---|---|
| 4.4.1 | Template-driven 5-Why + similar-report retrieval | Not Started |
| 4.4.2 | RCA API | Not Started |
| 4.4.3 | RCA UI workspace | Not Started |

## Milestone 4.5 — Compliance Intelligence Center

| Task ID | Task | Status |
|---|---|---|
| 4.5.1 | Requirements / evidence / gap detection (checklist-based, Python) | Not Started |
| 4.5.2 | Compliance APIs | Not Started |
| 4.5.3 | Compliance Center UI | Not Started |

## Milestone 4.6 — Analytics

| Task ID | Task | Status |
|---|---|---|
| 4.6.1 | Fleet coverage + indexing velocity APIs | Not Started |
| 4.6.2 | Analytics UI charts | Not Started |

## Milestone 4.7 — Cross-Document Reasoning Hardening

| Task ID | Task | Status |
|---|---|---|
| 4.7.1 | Multi-hop retrieval plans for demo questions | Not Started |
| 4.7.2 | Numeric claim verification against `test_measurements` | Not Started |

## Milestone 4.8 — Industrial AI Validation Gate

| Task ID | Task | Status |
|---|---|---|
| 4.8.1 | Run Phase 4 checklists | Not Started |
| 4.8.2 | Mark Phase 4 Complete | Not Started |

---

## Milestone 5.1 — RBAC Hardening

| Task ID | Task | Status |
|---|---|---|
| 5.1.1 | Enforce role permissions on routes | Not Started |
| 5.1.2 | Document ACL filtering before retrieval/LLM | Not Started |
| 5.1.3 | Admin user/role management APIs + UI minimum | Not Started |

## Milestone 5.2 — Audit Logs

| Task ID | Task | Status |
|---|---|---|
| 5.2.1 | Immutable audit event writer | Not Started |
| 5.2.2 | Cover login, upload, view, copilot, export, admin | Not Started |
| 5.2.3 | Audit export API | Not Started |

## Milestone 5.3 — Caching Strategy

| Task ID | Task | Status |
|---|---|---|
| 5.3.1 | Cache Asset 360 expensive aggregates | Not Started |
| 5.3.2 | Cache summaries/recommendations/health where safe | Not Started |
| 5.3.3 | Invalidation rules on indexing/graph updates | Not Started |

## Milestone 5.4 — Background Worker Hardening

| Task ID | Task | Status |
|---|---|---|
| 5.4.1 | Retries, dead-letter, idempotency audits | Not Started |
| 5.4.2 | Rate-limit aware Drive sync | Not Started |
| 5.4.3 | Progress SSE/WebSocket reliability | Not Started |

## Milestone 5.5 — Monitoring & Observability

| Task ID | Task | Status |
|---|---|---|
| 5.5.1 | Metrics for API latency, job queue depth, indexing velocity | Not Started |
| 5.5.2 | Error tracking hooks | Not Started |
| 5.5.3 | Health dashboards for ops | Not Started |

## Milestone 5.6 — Security Hardening

| Task ID | Task | Status |
|---|---|---|
| 5.6.1 | Rate limiting | Not Started |
| 5.6.2 | Upload sanitization | Not Started |
| 5.6.3 | Prompt-injection defenses (context isolation + citation verify) | Not Started |
| 5.6.4 | CORS lock + secrets hygiene check | Not Started |

## Milestone 5.7 — Enterprise Validation Gate

| Task ID | Task | Status |
|---|---|---|
| 5.7.1 | Run Phase 5 checklists | Not Started |
| 5.7.2 | Mark Phase 5 Complete | Not Started |

---

## Milestone 6.1 — Automated Test Suite Expansion

| Task ID | Task | Status |
|---|---|---|
| 6.1.1 | Unit tests for extractors, chunking, health score, citations | Not Started |
| 6.1.2 | API tests for critical endpoints | Not Started |
| 6.1.3 | Integration tests for indexing pipeline | Not Started |

## Milestone 6.2 — Golden Evaluation Dataset

| Task ID | Task | Status |
|---|---|---|
| 6.2.1 | Curate demo Q&A grounded in corpus (hackathon: ≥30; target 100+) | Not Started |
| 6.2.2 | Retrieval metrics harness (Recall@5, MRR) | Not Started |
| 6.2.3 | Citation accuracy / hallucination checks | Not Started |
| 6.2.4 | Run eval before demo | Not Started |

## Milestone 6.3 — E2E & Demo Reliability Gates

| Task ID | Task | Status |
|---|---|---|
| 6.3.1 | Playwright path: Explorer → Asset 360 → Copilot citation visible | Not Started |
| 6.3.2 | Smoke test gate in CI/deploy | Not Started |
| 6.3.3 | Pre-cache hero motor summary/health/recs | Not Started |

## Milestone 6.4 — Bug Fix & UX Polish

| Task ID | Task | Status |
|---|---|---|
| 6.4.1 | Triage demo-blocking bugs | Not Started |
| 6.4.2 | Enterprise density UX pass on Asset 360 | Not Started |
| 6.4.3 | Remove leftover jargon / placeholders | Not Started |

## Milestone 6.5 — Deployment

| Task ID | Task | Status |
|---|---|---|
| 6.5.1 | Deploy API (Azure Container Apps or equivalent) | Not Started |
| 6.5.2 | Deploy frontend (Vercel or equivalent) | Not Started |
| 6.5.3 | Configure managed PG/Redis/Neo4j/Qdrant/Blob as needed | Not Started |
| 6.5.4 | Environment secrets verification | Not Started |

## Milestone 6.6 — Demo Video, Presentation & Architecture Slides

| Task ID | Task | Status |
|---|---|---|
| 6.6.1 | Rehearse 7-minute single-motor journey (Architecture §16) | Not Started |
| 6.6.2 | Record backup walkthrough video | Not Started |
| 6.6.3 | Judge slides (product language rules) | Not Started |

## Milestone 6.7 — Documentation Sync

| Task ID | Task | Status |
|---|---|---|
| 6.7.1 | README runbooks (local + deploy) | Not Started |
| 6.7.2 | Update this Implementation Plan statuses to final | Not Started |
| 6.7.3 | Note known limitations honestly | Not Started |

## Milestone 6.8 — Final Release Validation Gate

| Task ID | Task | Status |
|---|---|---|
| 6.8.1 | Full release checklist | Not Started |
| 6.8.2 | Declare Version 1 demo-ready | Not Started |

---

# 7. Subtask Breakdown

Subtasks define the micro-execution steps and Definition of Done for each task family. When implementing a task, complete its subtasks in order.

---

## 7.1 Pattern Applied to Every Task

Every task must be executed as:

1. Confirm dependencies satisfied  
2. Implement minimum necessary files only  
3. Wire configuration via env  
4. Add/adjust typed schemas  
5. Add structured logs  
6. Add or update tests required by milestone DoD  
7. Run validation steps  
8. Update Progress Tracker  

---

## 7.2 Milestone 1.1 Subtasks (Example Fully Expanded)

### Task 1.1.1 — Create monorepo / workspace layout

| Subtask | DoD |
|---|---|
| Create `backend/`, `frontend/`, `docs/`, `docker/` (only if needed) | Folders exist; no empty junk dirs |
| Confirm Architecture module map for `backend/app/` | Matches Architecture §9 names |
| Verify no conflicting legacy code | Greenfield clean |

### Task 1.1.2 — Initialize backend Python project

| Subtask | DoD |
|---|---|
| Create pyproject/requirements | Installable |
| Pin core deps: fastapi, uvicorn, sqlalchemy, alembic, pydantic-settings, httpx, celery/redis clients | Documented in `.env.example` counterparts |
| Local `uvicorn` boot smoke | Health route later; import works |

### Task 1.1.3 — Initialize frontend Next.js TypeScript app

| Subtask | DoD |
|---|---|
| `create-next-app` App Router + TS | App runs |
| Tailwind configured | Styles compile |
| Base path structure `app/` | Ready for shell |

### Task 1.1.4 — README / env / gitignore

| Subtask | DoD |
|---|---|
| `.env.example` lists all required keys (no secrets) | Complete |
| `.gitignore` excludes `.env`, caches, node_modules, venv | Safe |
| README explains boot commands | Copy-pasteable |

### Task 1.1.5 — Tooling baselines

| Subtask | DoD |
|---|---|
| Ruff/black or project-standard Python lint | Command documented |
| ESLint/Prettier frontend | Command documented |
| pytest configured | `pytest` collects zero/pass |

**Milestone 1.1 Definition of Done:** repo boots locally for API+web skeletons; tooling commands documented; tracker updated.

---

## 7.3 Milestone 1.2 Subtasks — Backend Foundation

### Initialize FastAPI

| Subtask | Status |
|---|---|
| Create application factory | Complete |
| Mount routers under `/api/v1` | Complete |
| Add `/health` and `/ready` | Complete |
| Verify OpenAPI at `/docs` | Complete |
| Run locally | Complete |

### Project Settings

| Subtask | Status |
|---|---|
| `Settings` class from env | Complete |
| Separate `dev`/`prod` safe defaults | Complete |
| Fail fast on missing critical secrets in prod mode | Complete |

### DI / Middleware / Errors / Envelope

| Subtask | Status |
|---|---|
| Depends-based service injection | Complete |
| CORS from settings | Complete |
| Request ID middleware | Complete |
| Exception handlers → `{ data, meta, errors }` | Complete |
| Machine-readable `error_code` | Complete |

**Milestone 1.2 DoD:** FastAPI app documented in OpenAPI; health OK; errors typed; settings via env; project runnable. **Met — 2026-07-17.**

---

## 7.4 Milestone 1.3 Subtasks — Database

| Subtask | Status |
|---|---|
| Alembic env + first migration | Complete |
| Create SoR tables per Architecture §12 (asset-agnostic + motor tables + documents + drawing links + jobs) | Complete |
| Repository interfaces for assets/documents | Complete |
| Seed product_line ABB LV Motors placeholder | Complete |
| Verify migrations up/down on fresh DB | Complete |

**DoD:** Fresh `docker compose` DB migrates cleanly; repositories can CRUD catalog stub; no business logic in models. **Met — 2026-07-17** (migration up/down verified via SQLite smoke; full PostgreSQL via Compose deferred to Milestone 1.9).

---

## 7.5 Milestone 1.4–1.11 Subtasks (Compressed Checklist Form)

### 1.4 Authentication

- [x] Choose JWT seed **or** Clerk/Auth0 (hackathon velocity) — **JWT seed chosen**
- [x] Implement login/refresh/me  
- [x] Protect API routes  
- [x] Seed RBAC role rows  
- [x] Frontend session persists  

**Milestone 1.4 DoD met — 2026-07-17.**

### 1.5 Storage

- [x] Storage port + Azure/MinIO adapter (+ local filesystem for offline/dev)
- [x] Upload stream from Drive/manual (service API; HTTP upload in 1.7)
- [x] Download / signed URL
- [x] MIME/size validation

**Milestone 1.5 DoD met — 2026-07-19.**

### 1.6 Google Drive

- [x] Auth works against shared corpus — **local root access check** (Drive API deferred)
- [x] Paginated discovery writes catalog
- [x] Checkpoints survive restart
- [x] Selective download to blob
- [x] Sync status endpoint

**Milestone 1.6 DoD met — 2026-07-19** (local corpus source; Drive-shaped contracts).

### 1.7 Catalog & Upload

- [x] Catalog reflects ≈ full discovery count  
- [x] Manual upload creates document + storage object  
- [x] Path-based `doc_category` / `doc_subtype`  
- [x] Filename drawing-number stubs linked  

**Milestone 1.7 DoD met — 2026-07-19** (catalog APIs + manual upload + stub linking).

### 1.8 Frontend Shell

- [x] Sidebar matches Architecture nav  
- [x] Placeholder routes render without crashing  
- [x] Auth gate works  
- [x] API client authenticated  

**Milestone 1.8 DoD met — 2026-07-19** (enterprise shell + auth gate + Query client).

### 1.9 Docker

- [x] `docker compose up` starts dependencies
- [x] API + web reachable
- [x] Volumes persist PG/Qdrant/Neo4j

**Milestone 1.9 DoD met — 2026-07-20** (Compose stack + Dockerfiles + one-command boot docs).

### 1.10 Logging

- [x] JSON logs with request_id
- [x] No `print()` in app code
- [x] Pipeline-ready logger names by module

**Milestone 1.10 DoD met — 2026-07-20** (JSON logging + correlation IDs + latency metrics hooks).

### 1.11 Gate

- [ ] All Phase 1 DoDs pass  
- [ ] Tracker marks Phase 1 Complete  
- [ ] Only then unlock Phase 2  

---

## 7.6 Phase 2–6 Subtask Standard (Apply Per Task)

For each remaining task, Cursor must expand subtasks at implementation time using this template and record completion in the tracker notes:

```
Task: <ID> <Name>
Subtasks:
  1. Design fit check vs Architecture (where it belongs)
  2. Implement service + repository + schema (only needed layers)
  3. Wire API route (if any) with validation
  4. Add logs + config
  5. Tests required by milestone
  6. Manual validation steps
  7. Update IMPLEMENTATION_PLAN.md tracker
Definition of Done:
  - Feature works for hero-motor path (or foundation path)
  - No architecture drift
  - No unnecessary files
  - Project still runnable
```

**Phase 2 critical expanded DoDs:**

| Milestone | Must Prove |
|---|---|
| 2.1 | Tier router selects correct parser; Azure DI extracts a test-report table |
| 2.2 | Drawing numbers extracted; test measurements stored |
| 2.3 | Chunks carry required metadata payload |
| 2.4 | Embeddings versioned |
| 2.5 | Filtered vector search returns hero-motor chunks |
| 2.6 | Cypher from MotorModel center returns linked docs |
| 2.7 | Hybrid retrieval returns reranked top results |
| 2.8 | Citations resolve to real chunks |
| 2.9 | Priority queue processes test reports before drawings; status API live |

**Phase 3 critical expanded DoDs:**

| Milestone | Must Prove |
|---|---|
| 3.1 | Hero motor selected; hierarchy queryable |
| 3.2 | Explorer filters work at catalog scale |
| 3.3 | Bundle API returns all Asset 360 zones |
| 3.4 | Timeline chronological with honest estimated badges |
| 3.5 | Summary fields cited or “Not available…” |
| 3.6 | Score deterministic; bullets evidence-backed; LLM does not own score |
| 3.7 | 3–5 recommendation cards with citations |
| 3.8 | Drawing cross-ref shows multi-folder docs |
| 3.9 | Graph UI motor-centered |
| 3.10 | Unified search returns motors + docs |
| 3.11 | Dashboard shows discovered/indexed/processing counts |
| 3.12 | Flagship page demo-ready for hero motor |

**Phase 4–6:** Apply same template; Copilot must stream citations; compliance/health remain Python-owned; golden eval runs before demo.

---

# 8. Dependency Graph

## 8.1 Phase Dependencies

```
Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6
```

No parallel phases. Within a phase, some milestones may run parallel only if listed below.

## 8.2 Milestone Dependencies (Phase 1)

| Milestone | Depends On | Required Before | Can Run Parallel With | Blocked By |
|---|---|---|---|---|
| 1.1 Bootstrap | — | All later | — | Missing repo access |
| 1.2 Backend Foundation | 1.1 | 1.3+ | — | 1.1 incomplete |
| 1.3 Database | 1.2 | 1.4, 1.6, 1.7 | — | 1.2 incomplete |
| 1.4 Auth | 1.3 | 1.8 (frontend auth), APIs | 1.5 | 1.3 incomplete |
| 1.5 Storage | 1.2 | 1.6 download, 1.7 upload | 1.4 | Storage creds |
| 1.6 Google Drive | 1.3, 1.5 | 1.7 enrichment, Phase 2 | — | Drive API access |
| 1.7 Catalog & Upload | 1.6 | Phase 2 | — | 1.6 discovery |
| 1.8 Frontend Shell | 1.1 | Phase 3 UI | 1.9 after 1.2 | — |
| 1.9 Docker | 1.2, 1.3 | Phase 2 services usage | 1.8 | — |
| 1.10 Logging | 1.2 | All later quality | 1.3–1.9 | — |
| 1.11 Validation Gate | 1.1–1.10 | Phase 2 | — | Any P1 blocker |

## 8.3 Milestone Dependencies (Phase 2)

| Milestone | Depends On | Required Before | Can Run Parallel With | Blocked By |
|---|---|---|---|---|
| 2.1 Parsing | Phase 1 | 2.2, 2.3 | — | Parser creds/quota |
| 2.2 Extraction | 2.1 | 2.6, 3.1 enrichment | 2.3 (partial) | Poor parse quality |
| 2.3 Chunking | 2.1 | 2.4 | 2.2 | — |
| 2.4 Embeddings | 2.3 | 2.5 | — | Embedding API |
| 2.5 Qdrant | 2.4 | 2.7 | 2.6 | Qdrant down |
| 2.6 Neo4j Sync | 2.2 | 2.7, Phase 3 graph UI | 2.5 | Neo4j down |
| 2.7 Hybrid Retrieval | 2.5, 2.6 | 2.8, Phase 4 | — | Empty indexes |
| 2.8 Citations | 2.7 | Phase 4 Copilot | — | — |
| 2.9 Indexing Workers | 2.1–2.6 | Phase 3 scale narrative | early skeleton after 1.9 | Redis/Celery |
| 2.10 Gate | 2.1–2.9 | Phase 3 | — | Hero evidence missing |

## 8.4 Milestone Dependencies (Phase 3)

| Milestone | Depends On | Required Before | Can Run Parallel With |
|---|---|---|---|
| 3.1 Asset Registry | 2.2, 1.7 | 3.2–3.12 | — |
| 3.2 Explorer | 3.1 | 3.12 navigation | 3.11 |
| 3.3 360 API | 3.1, 2.6, 2.7 | 3.12 | 3.4 |
| 3.4 Timeline | 3.1, 2.2 | 3.12 | 3.5 |
| 3.5 Summary | 2.7, 2.8, 3.1 | 3.12 | 3.6 |
| 3.6 Health | 2.2, 3.1 | 3.12 | 3.5 |
| 3.7 Recommendations | 3.3, 2.7 | 3.12 | — |
| 3.8 Drawings | 2.6 | Demo Act drawing | 3.9 |
| 3.9 Graph UI | 2.6 | Demo Act graph | 3.8 |
| 3.10 Search | 2.7, 3.1 | — | 3.8 |
| 3.11 Dashboard | 1.7, 2.9 | Demo Act 1 | 3.2 |
| 3.12 360 UI | 3.3–3.7, 3.4 | Phase 4 embed polish | — |
| 3.13 Gate | 3.1–3.12 | Phase 4 | — |

## 8.5 Milestone Dependencies (Phase 4–6)

| Milestone | Depends On | Notes |
|---|---|---|
| 4.1 Router | 2.7, 3.1 | Before Copilot |
| 4.2 Copilot | 4.1, 2.8, 3.3 | Flagship AI |
| 4.3 Maintenance | 2.2 test measurements | Parallel with 4.5 after 4.1 |
| 4.4 RCA | 4.3, 2.7 | Test-anomaly framing only |
| 4.5 Compliance | 3.1, 2.2 | Python gap logic |
| 4.6 Analytics | 2.9, 3.11 | Parallel late |
| 4.7 Reasoning harden | 4.2 | Before demo |
| 4.8 Gate | 4.1–4.7 | Unlocks Phase 5 |
| 5.x | Phase 4 gate | Hackathon may take MVP subset but still sequential inside 5.x |
| 6.x | Phase 5 gate (or explicit user-approved MVP freeze) | Do not start polish while core demo path broken |

## 8.6 Parallelization Rules

Allowed parallels are **only** those listed in “Can Run Parallel With.”  
If unsure: **do not parallelize** — finish the earlier milestone.

---

# 9. Deliverables

Only list what **should** exist per Architecture. Do not invent extras.

## 9.1 Target Repository Layout (Canonical)

```
backend/
  app/
    api/                 # REST routes (/api/v1)
    auth/                # RBAC middleware
    gdrive/              # Google Drive discovery + sync
    indexing/            # Continuous Intelligent Indexing + priority
    motors/              # Asset registry (motor hierarchy specialization)
    extraction/          # Drawing numbers, test tables, specs
    knowledge/           # Hybrid retrieval (internal)
    graph/               # Neo4j sync (derived)
    motor360/            # Asset 360 aggregation
    timeline/            # Lifecycle timeline
    summary/             # AI summary + cache
    health/              # Deterministic health/risk score
    recommendations/     # Recommendation engine
    agents/              # LangGraph agents
    reasoning/           # Maintenance + anomaly analysis
    citations/           # Provenance
    observability/       # Logging, metrics, eval hooks
  alembic/
  tests/
frontend/
  app/                   # Next.js App Router pages
  components/
  lib/                   # API client, auth helpers
docker/                  # Compose & Dockerfiles (or root compose)
docs/
  IMPLEMENTATION_PLAN.md # This file
```

> Module folders are created **when their milestone starts**, not all upfront.

## 9.2 Deliverables by Milestone (Expected Artifacts)

### Phase 1

| Milestone | Files / Folders | Services | Routes | DB Tables | Frontend | Workers | Tests | Docs |
|---|---|---|---|---|---|---|---|---|
| 1.1 | `backend/`, `frontend/`, `.env.example`, README | — | — | — | app skeleton | — | tooling smoke | README |
| 1.2 | `app` entry, settings, middleware, errors | settings | `/health`, `/ready`, `/api/v1/...` | — | — | — | health test | OpenAPI |
| 1.3 | models, repos, alembic | DB session | — | users/roles, assets/motors, documents, drawing_*, indexing_jobs, gdrive_sync_state | — | — | migration test | — |
| 1.4 | auth module | auth service | login/refresh/me | users, roles, user_roles | login/session | — | auth tests | — |
| 1.5 | storage adapter | storage service | internal | — | — | — | storage unit | — |
| 1.6 | `gdrive/` | drive client, discovery | sync start/status | gdrive_sync_state, document_catalog | `/sync` shell | discovery job | drive integration | — |
| 1.7 | documents APIs | catalog/upload services | documents CRUD-ish | document_catalog, documents, versions | `/documents` shell | — | upload test | — |
| 1.8 | Next.js shell + nav | — | — | — | all primary nav shells | — | — | — |
| 1.9 | Dockerfiles, compose | PG, Redis, MinIO, Neo4j, Qdrant | — | — | — | redis | compose smoke | README boot |
| 1.10 | logging config | observability | — | — | — | — | log format assert | — |
| 1.11 | — | — | — | — | — | — | Phase 1 suite | tracker update |

### Phase 2

| Milestone | Key Artifacts |
|---|---|
| 2.1 | `extraction`/`indexing` parsers; Azure DI + PyMuPDF handlers |
| 2.2 | entity extractors; `extraction_candidates`; `test_measurements` |
| 2.3 | chunkers; `document_chunks` |
| 2.4 | embedding abstraction; `embedding_registry` |
| 2.5 | Qdrant collection + upsert service |
| 2.6 | Neo4j constraints; sync service; Cypher queries |
| 2.7 | `knowledge/` hybrid retrieval + rerank |
| 2.8 | `citations/` formatter + verifier; `retrieval_traces` |
| 2.9 | Celery tasks; priority queue; indexing status APIs |
| 2.10 | Validation evidence for hero motor chain |

### Phase 3

| Milestone | Key Artifacts |
|---|---|
| 3.1 | `motors/` registry APIs + tables enriched |
| 3.2 | `/motors` Explorer UI + list/search API |
| 3.3 | `motor360/` bundle API |
| 3.4 | `timeline/` service + events table usage |
| 3.5 | `summary/` + `motor_ai_summaries` |
| 3.6 | `health/` + `motor_health_scores` |
| 3.7 | `recommendations/` + cache table |
| 3.8 | Drawing Explorer page + APIs |
| 3.9 | `/graph` UI + subgraph API |
| 3.10 | `/search` UI + API |
| 3.11 | `/dashboard` + `/sync` progress UX |
| 3.12 | `/motors/[id]` flagship page |
| 3.13 | Hero motor demo checklist signed off |

### Phase 4

| Milestone | Key Artifacts |
|---|---|
| 4.1 | query router in `agents/` or `knowledge/` |
| 4.2 | LangGraph copilot; SSE chat; `/copilot`; sessions/messages tables |
| 4.3 | `/maintenance` + reasoning services |
| 4.4 | RCA APIs + UI |
| 4.5 | `/compliance` + requirements/evidence tables usage |
| 4.6 | `/analytics` |
| 4.7 | numeric claim verification hooks |
| 4.8 | Phase 4 gate |

### Phase 5

| Milestone | Key Artifacts |
|---|---|
| 5.1 | enforced RBAC + ACL filters |
| 5.2 | `audit_events` complete coverage |
| 5.3 | Redis cache layers for 360 aggregates |
| 5.4 | worker retries/DLQ |
| 5.5 | metrics endpoints/exporters |
| 5.6 | rate limits, upload guards, CORS hardening |
| 5.7 | Phase 5 gate |

### Phase 6

| Milestone | Key Artifacts |
|---|---|
| 6.1 | expanded pytest suite |
| 6.2 | golden eval dataset + harness |
| 6.3 | Playwright e2e + smoke gate |
| 6.4 | polished Asset 360 UX |
| 6.5 | deployed environments |
| 6.6 | demo video + slides |
| 6.7 | docs synced |
| 6.8 | V1 demo-ready declaration |

---

# 10. Definition of Done

## 10.1 Universal Milestone DoD (Apply Always)

A milestone is **Complete** only if **all** are true:

- [ ] Scope matches Architecture (no drift, no new modules)  
- [ ] Backend compiles / typechecks as applicable  
- [ ] Frontend builds (if UI touched)  
- [ ] Docker Compose still boots (if infra touched)  
- [ ] APIs touched are OpenAPI-documented with typed schemas  
- [ ] Validation checklist for the milestone passed  
- [ ] Required tests for the milestone passed  
- [ ] Lint passes on touched code  
- [ ] No unexplained TODOs / stub dead ends (unless marked PLACEHOLDER with follow-up ID)  
- [ ] No duplicated services/models/repositories introduced  
- [ ] Structured logging present; no `print()`  
- [ ] Config via environment variables  
- [ ] Files created are justified and listed in the implementation notes  
- [ ] Progress Tracker updated  
- [ ] Project remains runnable  

## 10.2 Phase Gates (Additional)

| Phase Gate | Extra Required Proof |
|---|---|
| Phase 1 | Drive discovery catalog non-zero; auth works; compose healthy |
| Phase 2 | Hero motor has parsed chunks in Qdrant + graph links in Neo4j; retrieval returns citations |
| Phase 3 | Hero Motor Asset 360 all zones populated for demo |
| Phase 4 | Three demo Copilot questions answer with citations on hero motor |
| Phase 5 | RBAC + audit on critical paths; security baseline |
| Phase 6 | Golden path e2e green; backup video exists; deploy reachable |

---

# 11. Validation Checklists

## 11.1 Per-Milestone Validation Dimensions

Every milestone checklist must cover the applicable subset:

| Dimension | When Required |
|---|---|
| Manual testing | Always |
| API testing | If routes changed |
| UI testing | If pages/components changed |
| Database testing | If schema/repos changed |
| Integration testing | If cross-module pipeline changed |
| Performance verification | If retrieval/indexing/copilot path changed |

## 11.2 Phase 1 Validation Checklist

**Manual**
- [ ] `docker compose up` succeeds  
- [ ] OpenAPI docs load  
- [ ] Login works; unauthorized denied  
- [ ] Drive sync starts and catalog count increases  
- [ ] Frontend shell navigates all primary routes  

**API**
- [ ] `/health` 200  
- [ ] `/api/v1/.../me` returns user  
- [ ] Documents list returns catalog rows  

**UI**
- [ ] Sidebar visible; responsive enough for demo laptop  
- [ ] Auth gate blocks protected pages  

**Database**
- [ ] Migrations apply on empty volume  
- [ ] Catalog rows persist after restart  

**Integration**
- [ ] Upload or Drive file lands in object storage + DB row  

**Performance**
- [ ] Discovery pagination does not hang first page (> reasonable timeout)  

## 11.3 Phase 2 Validation Checklist

**Manual**
- [ ] Priority job processes a performance test report  
- [ ] Drawing numbers appear for hero motor docs  

**API**
- [ ] Indexing status shows discovered/indexed/processing  
- [ ] Search/retrieval endpoint returns chunk hits with ids  

**Database**
- [ ] `document_chunks` and `test_measurements` populated for sample  

**Integration**
- [ ] Parse → extract → chunk → embed → Qdrant → Neo4j path succeeds for hero docs  

**Performance**
- [ ] Single doc pipeline finishes within acceptable demo latency  

## 11.4 Phase 3 Validation Checklist

**Manual / UI**
- [ ] Fleet Dashboard shows corpus scale stats  
- [ ] Explorer opens hero motor  
- [ ] Asset 360 shows summary, health bullets, recommendations, timeline, docs, mini-graph  

**API**
- [ ] Motor bundle endpoint complete  
- [ ] Health score recomputes deterministically  

**Database / Graph**
- [ ] Graph neighborhood rooted at motor  

**Integration**
- [ ] New indexed doc invalidates/refreshes summary cache  

## 11.5 Phase 4 Validation Checklist

**Manual / UI**
- [ ] Copilot answers 3 Architecture §16 questions with visible citations  
- [ ] Maintenance + Compliance pages show hero motor evidence  

**API**
- [ ] SSE stream stable  
- [ ] Feedback endpoint stores rating  

**Integration**
- [ ] Router selects correct tools for drawing vs test questions  

**Performance**
- [ ] P95 copilot latency acceptable for live demo (or graceful degrade)  

## 11.6 Phase 5 Validation Checklist

- [ ] Role restrictions enforced  
- [ ] Audit events written for copilot + upload + login  
- [ ] Cache hit path verified for Asset 360  
- [ ] Rate limit triggers  
- [ ] Secrets not in repo  

## 11.7 Phase 6 Validation Checklist

- [ ] Unit/API tests green  
- [ ] Golden eval run recorded  
- [ ] Playwright critical path green  
- [ ] Deployed URL stable  
- [ ] Backup video recorded  
- [ ] Demo rehearsal completed  

---

# 12. Progress Tracker

## 12.1 Phase Tracker

| Phase | Status | Progress | Owner | Dependencies | Completion Date | Notes |
|---|---|---|---|---|---|---|
| Phase 1 — Foundation | In Progress | 91% (10/11 milestones) | Engineering | Architecture Report | — | Milestone 1.10 Complete |
| Phase 2 — Document Intelligence | Not Started | 0% | Engineering | Phase 1 | — | — |
| Phase 3 — Asset Intelligence | Not Started | 0% | Engineering | Phase 2 | — | — |
| Phase 4 — Industrial AI | Not Started | 0% | Engineering | Phase 3 | — | — |
| Phase 5 — Enterprise | Not Started | 0% | Engineering | Phase 4 | — | Hackathon MVP subset allowed only after Phase 4 gate |
| Phase 6 — Testing & Polish | Not Started | 0% | Engineering | Phase 5 or explicit MVP freeze | — | — |

## 12.2 Milestone Tracker

| Milestone | Phase | Status | Progress | Owner | Dependencies | Completion Date | Notes |
|---|---|---|---|---|---|---|---|
| 1.1 Project Bootstrap | 1 | Complete | 100% | Engineering | — | 2026-07-17 | Monorepo + scaffolds + tooling; root README on GitHub (not duplicated locally) |
| 1.2 Backend Foundation | 1 | Complete | 100% | Engineering | 1.1 | 2026-07-17 | FastAPI factory, settings, DI, middleware, `/api/v1`, envelope, health/ready |
| 1.3 Database | 1 | Complete | 100% | Engineering | 1.2 | 2026-07-17 | SQLAlchemy/Alembic SoR schema, repos, ABB LV Motors seed |
| 1.4 Authentication | 1 | Complete | 100% | Engineering | 1.3 | 2026-07-17 | JWT seed login/refresh/me; protected routes; frontend session |
| 1.5 Object Storage | 1 | Complete | 100% | Engineering | 1.2 | 2026-07-19 | Port + local/MinIO/Azure adapters; upload/download/signed URL; MIME/size |
| 1.6 Google Drive Integration | 1 | Complete | 100% | Engineering | 1.3, 1.5 | 2026-07-19 | Local corpus discovery + checkpoint + selective download + sync API |
| 1.7 Document Catalog & Upload | 1 | Complete | 100% | Engineering | 1.6 | 2026-07-19 | Catalog list/stats/get; upload; classification; drawing/asset stubs |
| 1.8 Frontend Shell | 1 | Complete | 100% | Engineering | 1.1, 1.4 | 2026-07-19 | App Router shell; §10 sidebar; theme; Query; auth gate; placeholders |
| 1.9 Docker Compose Stack | 1 | Complete | 100% | Engineering | 1.2, 1.3, 1.8 | 2026-07-20 | Compose: api/web/pg/redis/minio/neo4j/qdrant; volumes; README boot |
| 1.10 Logging Foundation | 1 | Complete | 100% | Engineering | 1.2 | 2026-07-20 | JSON logs; request_id contextvars; get_logger; latency counters |
| 1.11 Foundation Validation Gate | 1 | Not Started | 0% | — | 1.1–1.10 | — | **ACTIVE** |
| 2.1 Parsing & OCR | 2 | Not Started | 0% | — | Phase 1 | — | — |
| 2.2 Metadata & Entity Extraction | 2 | Not Started | 0% | — | 2.1 | — | — |
| 2.3 Chunking | 2 | Not Started | 0% | — | 2.1 | — | — |
| 2.4 Embedding Pipeline | 2 | Not Started | 0% | — | 2.3 | — | — |
| 2.5 Qdrant Indexing | 2 | Not Started | 0% | — | 2.4 | — | — |
| 2.6 Neo4j Graph Sync | 2 | Not Started | 0% | — | 2.2 | — | — |
| 2.7 Hybrid Retrieval | 2 | Not Started | 0% | — | 2.5, 2.6 | — | — |
| 2.8 Citation Pipeline | 2 | Not Started | 0% | — | 2.7 | — | — |
| 2.9 Continuous Indexing Workers | 2 | Not Started | 0% | — | 2.1–2.6 | — | — |
| 2.10 Doc Intelligence Gate | 2 | Not Started | 0% | — | 2.1–2.9 | — | — |
| 3.1 Asset Registry | 3 | Not Started | 0% | — | Phase 2 | — | — |
| 3.2 Asset Explorer | 3 | Not Started | 0% | — | 3.1 | — | — |
| 3.3 Asset 360 API | 3 | Not Started | 0% | — | 3.1, 2.6, 2.7 | — | — |
| 3.4 Timeline | 3 | Not Started | 0% | — | 3.1 | — | — |
| 3.5 AI Summary | 3 | Not Started | 0% | — | 2.7, 2.8 | — | — |
| 3.6 Health Score | 3 | Not Started | 0% | — | 2.2, 3.1 | — | Python-only scoring |
| 3.7 Recommendations | 3 | Not Started | 0% | — | 3.3, 2.7 | — | — |
| 3.8 Drawing Explorer | 3 | Not Started | 0% | — | 2.6 | — | — |
| 3.9 Knowledge Graph UI | 3 | Not Started | 0% | — | 2.6 | — | — |
| 3.10 Unified Search | 3 | Not Started | 0% | — | 2.7, 3.1 | — | — |
| 3.11 Fleet Dashboard | 3 | Not Started | 0% | — | 1.7, 2.9 | — | — |
| 3.12 Asset 360 Frontend | 3 | Not Started | 0% | — | 3.3–3.7 | — | Flagship |
| 3.13 Asset Intelligence Gate | 3 | Not Started | 0% | — | 3.1–3.12 | — | — |
| 4.1 Query Router | 4 | Not Started | 0% | — | Phase 3 | — | — |
| 4.2 Industrial Copilot | 4 | Not Started | 0% | — | 4.1, 2.8 | — | — |
| 4.3 Maintenance Intelligence | 4 | Not Started | 0% | — | 2.2 | — | — |
| 4.4 RCA | 4 | Not Started | 0% | — | 4.3 | — | Test-anomaly RCA |
| 4.5 Compliance | 4 | Not Started | 0% | — | 3.1 | — | — |
| 4.6 Analytics | 4 | Not Started | 0% | — | 2.9 | — | — |
| 4.7 Cross-doc Reasoning | 4 | Not Started | 0% | — | 4.2 | — | — |
| 4.8 Industrial AI Gate | 4 | Not Started | 0% | — | 4.1–4.7 | — | — |
| 5.1 RBAC | 5 | Not Started | 0% | — | Phase 4 | — | — |
| 5.2 Audit Logs | 5 | Not Started | 0% | — | 5.1 | — | — |
| 5.3 Caching | 5 | Not Started | 0% | — | 3.3 | — | — |
| 5.4 Worker Hardening | 5 | Not Started | 0% | — | 2.9 | — | — |
| 5.5 Monitoring | 5 | Not Started | 0% | — | 1.10 | — | — |
| 5.6 Security Hardening | 5 | Not Started | 0% | — | 5.1 | — | — |
| 5.7 Enterprise Gate | 5 | Not Started | 0% | — | 5.1–5.6 | — | — |
| 6.1 Tests Expansion | 6 | Not Started | 0% | — | Phase 5 | — | — |
| 6.2 Golden Eval | 6 | Not Started | 0% | — | 4.2 | — | — |
| 6.3 E2E Gates | 6 | Not Started | 0% | — | 3.12, 4.2 | — | — |
| 6.4 UX Polish | 6 | Not Started | 0% | — | 3.12 | — | — |
| 6.5 Deployment | 6 | Not Started | 0% | — | 6.3 | — | — |
| 6.6 Demo Assets | 6 | Not Started | 0% | — | 3.12, 4.2 | — | — |
| 6.7 Documentation Sync | 6 | Not Started | 0% | — | all | — | — |
| 6.8 Final Gate | 6 | Not Started | 0% | — | 6.1–6.7 | — | — |

## 12.3 Task Status Legend

| Status | Meaning |
|---|---|
| Not Started | No work begun |
| In Progress | Active implementation scope |
| Blocked | Waiting on dependency/external access |
| Complete | DoD + validation passed; tracker updated |

---

# 13. Future Prompt Rules (For Cursor)

These rules are **self-instructions**. Follow automatically without user reminder.

1. **Always read this file first** before coding.  
2. **Never work outside the active milestone** unless the user explicitly names a different milestone **and** its dependencies are Complete.  
3. **Never implement future milestones** opportunistically.  
4. **Always finish** the current task/milestone DoD before suggesting the next.  
5. **Always update** Active Execution Cursor + Progress Tracker.  
6. **Always validate** before marking Complete.  
7. **Always mention** files modified and files created.  
8. **Always explain why each new file exists** (single responsibility).  
9. **Never create unnecessary folders.**  
10. **Never duplicate** services, utilities, models, repositories, or APIs.  
11. **Never modify the Architecture Report** unless explicitly requested.  
12. **Never change technologies** or invent modules.  
13. **Never hardcode secrets.**  
14. **Never put business rules in LLM prompts** when Architecture assigns them to Python services.  
15. **Never expose RAG/embedding jargon** in UI copy.  
16. If a request would cause architecture drift: **pause, explain, propose Architecture-aligned alternative, then implement that.**  
17. After completing a milestone: **stop** and wait for the next user instruction (or explicit “continue to next milestone”).  
18. Prefer extending an existing module over creating a new one.  
19. Keep commits runnable (when user asks to commit).  
20. Keep this document synchronized with reality after every implementation session.  

---

# 14. Engineering Standards

## 14.1 Folder Organization

- Feature modules under `backend/app/<module>/`  
- Typical contents: `api` (or router), `service`, `repository`, `schema`, `model` — **only as needed**  
- Frontend routes under `frontend/app/` matching Architecture navigation  
- Tests mirror modules under `backend/tests/`  

## 14.2 Naming Conventions

| Kind | Convention |
|---|---|
| Python modules | `snake_case` |
| Classes | `PascalCase` |
| Functions / vars | `snake_case` |
| React components | `PascalCase.tsx` |
| API paths | `/api/v1/resource` plural nouns |
| DB tables | `snake_case` plural |
| Env vars | `SCREAMING_SNAKE_CASE` |
| Error codes | `SCREAMING_SNAKE_CASE` |

## 14.3 Dependency Injection

- FastAPI `Depends` for request-scoped resources  
- Services receive repositories via constructors/factories  
- No hidden global mutable state  

## 14.4 Configuration

- `pydantic-settings` (or equivalent) single Settings object  
- `.env` local; `.env.example` committed  
- Feature flags only if Architecture-needed  

## 14.5 Logging

- Structured JSON  
- Include `request_id`, module, job_id where relevant  
- Log pipeline stage transitions  

## 14.6 Error Handling

- Central handlers  
- Envelope `{ data, meta, errors }`  
- Stable `error_code` values (`ASSET_NOT_FOUND`, `INGESTION_FAILED`, `PERMISSION_DENIED`, …)  

## 14.7 Database Design

- PostgreSQL is system of record  
- Alembic migrations required for schema changes  
- Asset-agnostic `asset_type` discriminator; motor tables specialize hero domain  
- No Neo4j/Qdrant as SoR  

## 14.8 Repository Pattern

- Repositories own SQL  
- No business rules inside repositories  

## 14.9 Service Pattern

- Services own domain logic  
- Orchestrate repositories + external adapters  
- Keep routes thin  

## 14.10 DTOs / Schemas / Validation

- Pydantic request/response models for all public APIs  
- Zod (or equivalent) on frontend forms when needed  
- Never trust raw request bodies  

## 14.11 Type Safety

- Python type hints on public functions  
- TypeScript `strict` preferred  
- Avoid `Any` unless boundary-justified  

## 14.12 Testing

- pytest unit/API/integration  
- AI eval harness for retrieval/citations  
- Playwright for critical UX path  
- Testing begins in Phase 1 — not deferred entirely to Phase 6  

## 14.13 API Versioning

- All public HTTP APIs under `/api/v1/`  
- Breaking changes require new version — do not silently break clients  

## 14.14 Git Conventions

- Never develop directly on `main`  
- Feature branches  
- Meaningful commits focused on why  
- Commit only when user requests  

## 14.15 Documentation

- Prefer self-explanatory code  
- Update this Implementation Plan on progress  
- Avoid proliferating extra markdown files  

---

# 15. File Creation Policy

## 15.1 Mandatory Pre-Creation Checklist

Before creating **any** new file, answer:

1. Can existing code be reused or extended?  
2. Can this functionality live in an existing module?  
3. Is this file actually necessary for the active milestone?  
4. Does it increase maintainability (not just file count)?  
5. Does it have a **single clear responsibility**?  
6. Would Architecture §9/§23 endorse this file’s location?  

If any answer fails → **do not create the file**.

## 15.2 Prohibitions

- No duplicate helper utilities  
- No duplicate services / models / repositories / APIs  
- No speculative folders for future phases  
- No empty `__init__` sprawl beyond package needs  
- No “temporary” files without deletion plan  
- No parallel architecture experiments in-tree  

## 15.3 Preference Order

1. Extend existing service  
2. Add method to existing repository  
3. Add schema fields to existing DTO  
4. Create new file in existing module  
5. Create new module **only** if Architecture already defined it and milestone requires it  

## 15.4 When a New File Is Created

Document in the implementation response:

- Path  
- Responsibility  
- Why existing files were insufficient  
- Milestone/task ID it serves  

---

# 16. Implementation Tracking Rules

Whenever the user asks to implement anything, Cursor must automatically:

1. Identify **Current Phase**  
2. Identify **Current Milestone**  
3. Identify **Current Task** (or first Not Started task in milestone)  
4. Mark task **In Progress** in this document  
5. Implement **only that scope**  
6. Run **Validation Checklist** items that apply  
7. Update Progress Tracker percentages/notes  
8. Mark task **Complete** only if DoD met  
9. If milestone DoD met → mark milestone Complete; update Active Execution Cursor to next milestone  
10. Suggest the next task/milestone  
11. **Stop**  

### Progress Percentage Guidance

| Level | Formula |
|---|---|
| Milestone progress | Complete tasks / total tasks in milestone |
| Phase progress | Complete milestones / total milestones in phase |
| Overall progress | Weighted by phase gates (Phase 1–6); do not claim Phase 3 progress during Phase 1 |

---

# 17. Prompt Protocol

## 17.1 Standard User Prompts

### A) Build a milestone

**User:** `Build Milestone 1.2`

**Cursor must:**

1. Read `docs/IMPLEMENTATION_PLAN.md`  
2. Locate Milestone 1.2  
3. Verify dependencies (1.1 Complete)  
4. Implement only Milestone 1.2 tasks/subtasks  
5. Run Milestone 1.2 validations + DoD  
6. Update tracker (1.2 → Complete; set Active Cursor → 1.3)  
7. Summarize files created/modified + why  
8. **Stop — do not start Milestone 1.3**  

### B) Build a task

**User:** `Implement Task 1.6.2 Discovery Pass`

**Cursor must:** stay within Task 1.6.2; update only that task; stop.

### C) Continue

**User:** `Continue` / `Next milestone`

**Cursor must:** advance exactly one milestone (the next Not Started with deps satisfied), then stop.

### D) Status

**User:** `Where are we?`

**Cursor must:** answer from Active Execution Cursor + Phase/Milestone trackers only.

### E) Out-of-order request

If user asks for Phase 4 while Phase 1 incomplete:

1. Refuse to implement out of order  
2. Explain dependency  
3. Offer to continue the active milestone  

### F) Architecture conflict

If user asks for something that contradicts Architecture:

1. Pause  
2. Explain conflict with Architecture citation  
3. Propose aligned alternative  
4. Implement alternative only after alignment (or explicit user override documented in Assumptions Log)  

## 17.2 Required Response Footer (After Every Implementation)

```
Phase: <n>
Milestone: <id> <name> — <status>
Task: <id> <name> — <status>
Files created: ...
Files modified: ...
Validation: <pass/fail summary>
Tracker updated: yes
Next suggested: <milestone/task id>
```

## 17.3 Assumptions Log

| Date | Assumption | Impact | Resolution |
|---|---|---|---|
| 2026-07-16 | Architecture Report path may live outside `docs/` (Cursor plan file); this Implementation Plan is the execution SoT | Dev must not edit Architecture | Keep sync manually when Architecture explicitly updated |
| 2026-07-16 | Hackathon auth may be JWT seed users for speed | Faster Phase 1.4 | Swap to Clerk/Auth0 if required without redesign |
| 2026-07-16 | Google Drive API access available before deep indexing | Blocks 1.6 | rclone fallback per Architecture |
| 2026-07-16 | Non-motor domains catalog-first for hackathon | Phase 3 depth focuses on Motors | Asset-agnostic schema still required |
| 2026-07-16 | Golden eval target 100+; hackathon minimum ≥30 ABB-grounded pairs acceptable to unlock demo | Phase 6.2 | Expand post-hackathon |

Add rows whenever a new assumption is made during implementation.

## 17.4 Synchronization Rules

| Event | Action |
|---|---|
| Milestone completed | Update §§ Active Cursor, 5, 6, 12 |
| New blocker found | Set status Blocked + note |
| User explicitly changes Architecture | Update this plan to match; still do not edit Architecture unless asked |
| Scope cut for hackathon MVP | Document in Assumptions Log + adjust Phase 5/6 notes — do not silently delete Architecture requirements |

## 17.5 Demo-Critical Path (Do Not Lose)

Regardless of parallel interest items, the **must-not-fail** chain is:

```
1.6 Drive Discovery → 1.7 Catalog → 2.9 Priority Index (hero docs)
  → 2.6/2.7 Graph + Retrieval → 3.1 Hero Motor → 3.12 Asset 360
  → 4.2 Copilot with citations → 6.3/6.6 Demo reliability
```

All other work supports this chain; never jeopardize it for non-critical polish.

---

# Appendix A — Technology Lock (From Architecture §21)

| Area | Locked Choice |
|---|---|
| Product | Industrial Brain AI |
| Architecture style | Modular Monolith |
| Backend | FastAPI + Celery + Redis |
| Frontend | Next.js + shadcn/ui + Tailwind + TanStack Query |
| SoR | PostgreSQL |
| Graph | Neo4j |
| Vector | Qdrant |
| Agents | LangGraph |
| OCR (hackathon) | Azure DI + PyMuPDF (+ pdfplumber) |
| Embeddings (hackathon) | text-embedding-3-small or voyage-3 |
| LLM | GPT-4o / Claude + Gemini Flash router |
| Auth (hackathon) | Clerk/Auth0 or JWT seed |
| Deploy (hackathon) | Azure + Vercel + Docker + Google Drive API |

**Do not substitute** without an explicit Architecture change request.

---

# Appendix B — Module Ownership Map

| Module | Owns | Must Not Own |
|---|---|---|
| `gdrive` | Drive discovery/download | Parsing business rules |
| `indexing` | Priority queue + job orchestration | UI |
| `motors` | Asset registry hierarchy | LLM calls |
| `extraction` | Entities/measurements extraction | Vector upsert |
| `knowledge` | Hybrid retrieval | Final LLM narration (agents) |
| `graph` | Neo4j projection | PostgreSQL SoR writes of record |
| `motor360` | Aggregation bundle | Direct scraping of Drive |
| `timeline` | Lifecycle events assembly | Auth |
| `summary` | AI summary gen + cache | Health scoring |
| `health` | Deterministic score | LLM score ownership |
| `recommendations` | Recs agent + cache | Compliance gap math (shared carefully) |
| `agents` | Tool orchestration / Copilot | Raw SQL |
| `reasoning` | Maintenance/anomaly analysis | Frontend |
| `citations` | Provenance verify | Document storage |
| `auth` | Identity/RBAC | Domain scoring |
| `observability` | Logs/metrics/eval | Business decisions |
| `api` | HTTP adapters | Business logic |

---

# Appendix C — How to Resume After a Long Pause

1. Open `docs/IMPLEMENTATION_PLAN.md`  
2. Read **Active Execution Cursor**  
3. Read Phase/Milestone trackers for Blocked/In Progress items  
4. Skim Architecture only for the active module boundaries  
5. Continue the active task — do not restart the project  
6. Re-run the active milestone validation checklist before new coding if environment may have drifted  

---

**End of Implementation Plan Report**

**Governing relationship:** Architecture Report = design authority. This Implementation Plan = execution authority.  
**Development starts at:** Milestone **1.1 — Project Bootstrap**.  
**Next user prompt to begin coding:** `Build Milestone 1.1`
