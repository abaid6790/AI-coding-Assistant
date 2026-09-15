# Product Requirements Document — AI Coding Assistant

**Status:** Implemented (Phases 0–11 complete, plus a post-launch
restructure into the unified `src/` + `server/` layout)
**Last updated:** 2026-09-11

## 1. Overview

AI Coding Assistant is a multi-user, web-based developer tool that
combines a real code editor with AI-assisted code chat, generation,
debugging, review, optimization, test generation, and documentation
generation. It's built to feel like a lightweight, focused alternative
to tools like Cursor or GitHub Copilot Workspace, scoped to run on
modest hardware (an 8 GB RAM dev machine) without any local LLM.

## 2. Problem statement

Developers frequently switch context between their editor, a chat
window with an AI assistant, and separate tools for testing and
documentation. This project consolidates those into one authenticated,
per-user workspace where AI actions have full context of the actual
file being worked on, without requiring the user to copy-paste code
between tools.

## 3. Goals

- Give each user a private, isolated space for projects, files, AI
  conversations, and AI-generated artifacts (reviews, tests, docs).
- Make AI features (chat and the seven code-intelligence actions)
  context-aware of the current file/selection without ever sending an
  entire project to the AI provider.
- Keep the AI provider swappable — start with Gemini, but never let
  provider-specific code leak into routes, chat, or the UI.
- Never let AI-suggested changes silently overwrite a user's code —
  every suggestion is reviewable (diff view) before it's applied, and
  applying it still requires an explicit Save.
- Treat multi-user data isolation as a first-class, continuously-tested
  requirement, not an afterthought bolted onto existing routes.

## 4. Non-goals

- Executing user-submitted or AI-generated code on the server. This is
  a code *intelligence* tool, not a sandboxed code *execution* platform.
- Real-time multiplayer/collaborative editing (one user, one file, at a
  time — no operational-transform or CRDT layer).
- Local/self-hosted LLM support — cloud providers only, by design, to
  keep the resource footprint small.
- Version control / git integration (no commit history, branching, or
  diffing against a repo — only diffing an AI suggestion against the
  current draft).

## 5. Target users

Individual developers or small teams who want AI assistance embedded
directly in a lightweight web-based editor, without adopting a full IDE
extension or paying for a hosted product, and who are comfortable
self-hosting a Flask + React application.

## 6. Core features (implemented)

| # | Feature | Where it lives |
|---|---|---|
| 1 | Multi-user auth (register, email verification, login, password reset, change password) | `server/api/auth.py` |
| 2 | Project & file management with virtual folders, search | `server/api/projects.py`, `server/services/projects/project_service.py`, `src/pages/ProjectWorkspace.jsx` |
| 3 | Monaco-based code editor (syntax highlighting, format, copy, clear) | `src/components/code/CodeEditor.jsx` |
| 4 | Provider-agnostic AI architecture with Gemini key rotation | `server/services/ai/` |
| 5 | AI chat with controlled context selection (current file / selection / recent history) | `server/api/conversations.py`, `server/services/chat/chat_context.py`, `src/components/chat/ChatPanel.jsx` |
| 6 | Code Explain, Generate, Debug, Review, Optimize, Test generation, Documentation generation | `server/api/code.py`, `server/services/code/`, `src/components/code/AiActionsModal.jsx` |
| 7 | Diff review before any AI suggestion is applied | `src/components/code/DiffReviewModal.jsx` |
| 8 | Code Analysis Dashboard (quality/security/performance/maintainability trends) | `server/services/projects/project_service.py` (`get_project_analysis`), `src/components/analysis/AnalysisDashboardModal.jsx` |
| 9 | Toast notifications, empty/loading states, command palette | `src/context/ToastContext.jsx`, `src/components/chat/CommandPalette.jsx` |
| 10 | CSRF protection, file/path validation | `server/utils/csrf.py`, `server/utils/validation.py` |

## 7. Functional requirements

- A user must verify their email before logging in.
- A user can only ever see, modify, or delete their own projects,
  files, conversations, reviews, tests, and documents — enforced at the
  query layer (`server/utils/ownership.py`), not just the UI.
- AI features must never send an entire project's contents to the
  provider — only the current file (optionally truncated), an explicit
  selection, and a bounded slice of recent conversation history.
- An AI-suggested code change must be presented as a diff and require
  explicit user acceptance before it touches the editor's draft content.
- All AI provider errors must degrade gracefully: a user's chat message
  is persisted before the AI call runs, so a provider outage never loses
  what they typed.

## 8. Non-functional requirements

- **Security**: see `SECURITY.md` for the full checklist (CSRF, session
  handling, rate limiting, file validation, isolation testing).
- **Performance**: designed to run on an 8 GB RAM development machine —
  SQLite by default, no local LLM, Vite for fast frontend iteration.
- **Testability**: 135 backend tests covering auth, isolation,
  provider rotation, chat, code-intelligence features, and security
  hardening. (No frontend test suite yet — see Open items.)
- **Portability**: PostgreSQL-ready via `DATABASE_URL` without code
  changes (SQLAlchemy abstracts the swap).

## 9. Success metrics

Since this isn't a live product with real users yet, "success" here is
measured against the spec it was built from:

- All 20 phases of the original build plan implemented and tested.
- Zero known cross-user data leaks (backed by the isolation test suite).
- A new AI provider can be added by implementing one class and one line
  of registration — verified by the existing Groq/OpenRouter/Claude
  stubs following exactly that pattern.

## 10. Open items / future work

- Frontend automated test suite (Vitest + React Testing Library).
- CI pipeline running the backend suite (and frontend tests, once they
  exist) on every push.
- Dependency vulnerability scanning (`pip-audit`, `npm audit`, or
  Dependabot).
- A distributed rate-limit backend (Redis) for multi-worker production
  deployments.
- Real implementations for the Groq, OpenRouter, and Claude provider
  stubs.
- A project-scoped "quick open file" command (`Ctrl/Cmd+P`) to
  complement the global project-search command palette.
- Professional security review before any production deployment.

## 11. Reference

The full phase-by-phase build history and technical detail for every
feature above lives in `README.md`. This document exists as the
higher-level "what and why"; the README is the "how it works".
