# 🤖 AI Coding Assistant

> An AI-powered development workspace for managing projects, editing code, chatting with AI, reviewing and improving code, generating tests and documentation, and analyzing code quality — all from a unified web application.

**AI Coding Assistant** is a full-stack development environment built with **React, Vite, Tailwind CSS, Flask, SQLAlchemy, and provider-agnostic AI services**.

The project implements the complete feature set from **Phases 0–11**, including authentication, enforced multi-user data isolation, project and file management, a Monaco code editor, Gemini key rotation, contextual AI chat, seven AI-powered code-intelligence features, Monaco diff review, code analysis, command palette, toast notifications, CSRF protection, file validation, and a comprehensive automated test suite.

---

## ✨ Highlights

* 🔐 Complete authentication system
* 👥 Enforced multi-user data isolation
* 📁 Project and file management
* 📝 Virtual folder system
* 💻 Monaco-based code editor
* 🤖 Provider-agnostic AI architecture
* 🔑 Gemini API key rotation
* 💬 Context-aware AI chat
* 🧠 Seven AI code-intelligence features
* 🔍 Code review and quality analysis
* 📊 Code Analysis Dashboard
* 🔀 Monaco Diff Editor for AI changes
* 🧪 AI-generated tests
* 📚 AI-generated documentation
* 🔔 Toast notifications
* ⌘ Command palette
* 🛡️ CSRF protection
* 📂 Filename and path validation
* 🚦 API rate limiting
* 🧪 135 automated tests
* 🗄️ SQLite database
* ⚡ React + Vite frontend
* 🐍 Flask backend

---

# 📚 Documentation

| Document                             | Description                                            |
| ------------------------------------ | ------------------------------------------------------ |
| [`PRD.md`](PRD.md)                   | Product requirements, goals, architecture, and roadmap |
| [`CHANGELOG.md`](CHANGELOG.md)       | Phase-by-phase development history                     |
| [`SECURITY.md`](SECURITY.md)         | Security policy and hardening information              |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Development setup and contribution guidelines          |
| [`LICENSE`](LICENSE)                 | MIT License                                            |

---

# 🚀 Feature Overview

## 🔐 Authentication

The application provides a complete authentication workflow:

* User registration
* Login
* Logout
* Email verification
* Resend verification email
* Forgot password
* Password reset
* Change password
* Secure password hashing
* Session-based authentication
* Authentication rate limiting
* Generic authentication responses to reduce account enumeration

Verification and password-reset tokens are signed, time-limited, and tracked as single-use tokens.

---

# 👥 Multi-User Data Isolation

Multi-user isolation is a core security requirement of the application.

Every user can access only their own:

* Projects
* Files
* Conversations
* Reviews
* Generated tests
* Documentation
* Other owned resources

Ownership enforcement is centralized in:

```text
server/utils/ownership.py
```

This prevents individual routes from implementing inconsistent authorization logic.

### Isolation Rules

### 1. User ownership always comes from the session

The application never trusts a `user_id` supplied by the client.

The current user is obtained from the authenticated session.

For example, if a client sends:

```json
{
  "user_id": 999
}
```

the supplied user ID is ignored when determining ownership.

### 2. Unauthorized resources return 404

If a resource exists but belongs to another user, the application returns the same `404` response used for a nonexistent resource.

This prevents clients from learning whether another user's resource exists.

### 3. Centralized ownership helpers

Routes use:

```python
get_owned_or_404(Model, id)
```

and:

```python
owned_query(Model)
```

instead of unrestricted queries such as:

```python
Model.query.get(id)
```

or:

```python
Model.query.all()
```

### 4. File ownership has an additional project check

A file must belong to:

* The authenticated user
* The project referenced by the route

This prevents cross-project resource probing.

The isolation system is covered by dedicated automated tests.

---

# 📁 Project & File Management

Users can create and manage development projects and their files.

### Projects

* Create projects
* Rename projects
* Delete projects
* Search projects
* Open project workspace

### Files

* Create files
* Edit files
* Save files
* Delete files
* Rename files
* Select programming language
* Organize files using virtual folders

---

# 📂 Virtual Folders

The application does not use a separate database table for folders.

Instead, folders are represented through the `folder_path` stored with each file.

Example:

```text
src/
└── utils/
    └── helpers.py
```

The file can have:

```text
folder_path = "src/utils"
```

### Folder Behavior

* Folders exist only while they contain files.
* Creating a file inside a new folder automatically creates the folder logically.
* Renaming a folder updates the `folder_path` of all files beneath it.
* Nested folders are supported.

Example:

```text
src/utils/
src/utils/auth/
src/services/
```

Renaming:

```text
src/utils
```

to:

```text
src/helpers
```

updates all affected files and nested paths.

---

# 💻 Monaco Code Editor

The editor is powered by **Monaco Editor**, the editor technology used by Visual Studio Code.

[Monaco Editor React](https://github.com/suren-atoyan/monaco-react?utm_source=chatgpt.com)

### Editor Features

* Syntax-aware editing
* Language selector
* Line numbers
* Dark theme
* Copy
* Clear
* Format
* Save
* `Ctrl+S` / `Cmd+S`
* Unsaved/dirty state
* AI actions
* Code selection support

### Formatting

The Format action is available for languages where Monaco provides built-in formatting support, including:

* JavaScript
* TypeScript
* JSON
* HTML
* CSS

For unsupported languages, formatting is disabled rather than silently doing nothing.

### Monaco CDN Note

By default, the Monaco runtime is loaded through the package loader at browser runtime.

Therefore, the first editor load requires internet access.

The application itself can still run locally.

A completely offline Monaco setup would require self-hosting Monaco assets through the loader configuration. This is intentionally not included in the current implementation.

---

# 🤖 AI Architecture

The AI system is designed to be **provider-agnostic**.

The application communicates with an `AIService` abstraction instead of directly depending on a specific AI provider.

```text
AIService
    │
    ├── GeminiProvider
    │
    ├── GroqProvider
    │
    ├── OpenRouterProvider
    │
    └── ClaudeProvider
```

The architecture allows providers to be added without rewriting:

* Routes
* Chat functionality
* Code-intelligence features
* AI-related UI logic

---

# 🔑 Gemini API Key Rotation

Gemini is currently the implemented AI provider.

Multiple Gemini API keys can be configured.

Example:

```env
GEMINI_API_KEY_1=...
GEMINI_API_KEY_2=...
GEMINI_API_KEY_3=...
GEMINI_API_KEY_4=...
```

The provider rotates keys when failures indicate that another key may succeed.

Rotation occurs for:

* `429` — rate limit
* `401` — unauthorized/invalid key
* `403` — rejected key
* `5xx` — provider/server failure
* Network-level failures

An ordinary `400 Bad Request` does **not** trigger rotation because retrying the same invalid request with every key would unnecessarily consume quota.

### Sticky Key Behavior

Once a key successfully responds, it becomes the preferred key for subsequent requests.

This avoids repeatedly starting from an already exhausted key.

---

# 💬 AI Chat

The application includes a persistent AI chat system.

Each conversation consists of:

```text
Conversation
    │
    └── Messages
         ├── User
         └── Assistant
```

### Features

* Create conversations
* Persistent message history
* Automatic conversation titles
* Context selection
* Current-file context
* Selected-code context
* Regenerate responses
* Provider error handling

---

# 🧠 Controlled AI Context

The application intentionally limits how much project information is sent to the AI.

The default context can contain:

### Conversation History

Up to:

```text
10 messages
```

### Current File

When enabled:

```text
Maximum: 6,000 characters
```

### Selected Code

When using:

```text
Ask about selection →
```

the selected code is limited to:

```text
Maximum: 4,000 characters
```

Selected code takes precedence because it represents a more specific user instruction.

---

# 🔒 Context Isolation

Files used as AI context are validated against the conversation's project.

A file belonging to another project is silently excluded from the AI prompt.

This prevents accidental cross-project information leakage.

---

# 💾 Chat Failure Handling

User messages are persisted **before** the AI provider is called.

Therefore, if the AI provider becomes unavailable:

```text
User message
     ↓
Saved to database
     ↓
AI request
     ↓
Provider failure
```

the user's message is not lost.

The application returns an appropriate error while preserving the conversation state.

---

# 🧠 AI Code Intelligence

The application provides seven AI-powered development features:

| Feature       | Persistence | Purpose                             |
| ------------- | ----------- | ----------------------------------- |
| Explain       | Ephemeral   | Explain code and its behavior       |
| Generate      | Ephemeral   | Generate code from a description    |
| Debug         | Ephemeral   | Identify problems and suggest fixes |
| Review        | Persistent  | Review code quality and security    |
| Optimize      | Ephemeral   | Suggest improved code               |
| Tests         | Persistent  | Generate automated tests            |
| Documentation | Persistent  | Generate documentation              |

All features use the same `AIService` abstraction.

---

# 🔍 Explain

Analyzes the provided code and explains its behavior in natural language.

The feature can provide information about:

* Logic
* Structure
* Important functions
* Dependencies
* Potential issues
* Code flow

---

# ⚙️ Generate

Generates code from a natural-language description.

The system expects structured AI output but includes defensive parsing and raw-text fallback behavior when the model does not perfectly follow the expected format.

---

# 🐛 Debug

Analyzes code for potential problems and provides suggested corrections.

Important:

> AI-generated debugging results are suggestions, not guaranteed fixes.

The application explicitly marks debugging corrections as suggestions.

---

# 🔎 Code Review

Provides AI-assisted code review with findings categorized by severity:

* Critical
* High
* Medium
* Low
* Suggestion

Code reviews can also produce scores from:

```text
0–100
```

for areas such as:

* Quality
* Security
* Performance
* Maintainability

Reviews are persisted for future analysis.

---

# ⚡ Optimize

Analyzes code and generates an optimized version.

The response contains:

```text
original_code
optimized_code
```

The user can compare the two versions before applying the suggestion.

---

# 🧪 Tests

The application can generate tests based on the source code.

Supported frameworks include:

* pytest
* unittest
* Jest
* Mocha
* JUnit

Generated tests can be saved as a new project file.

---

# 📚 Documentation

The AI can generate multiple documentation formats, including:

* Docstrings
* Code comments
* README sections
* API documentation

Documentation is persisted for project history.

---

# 🔀 AI Diff Review

AI-generated code changes are **not automatically written into the editor**.

Instead, the application opens a Monaco `DiffEditor`.

```text
Current Code
     │
     ├──────────────┐
     │              │
     ▼              ▼
Original         AI Suggestion
     │              │
     └──────┬───────┘
            ▼
        Diff Review
        /         \
    Accept       Reject
```

### Accept

Applying the change:

* Updates the editor draft
* Marks the file as dirty
* Requires an explicit Save

### Reject

Rejecting the suggestion:

* Leaves the draft unchanged
* Does not modify the file
* Does not trigger a save

This prevents AI-generated changes from silently overwriting user code.

---

# 📊 Code Analysis Dashboard

The Code Analysis Dashboard provides project-level visibility into AI-assisted code reviews.

It includes:

* Latest quality score
* Security score
* Performance score
* Maintainability score
* Complexity summary
* Issues found
* Severity breakdown
* Review history
* Quality trend

Scores are explicitly presented as:

> **AI-assisted estimates, not certifications.**

### Quality Trend

The dashboard displays a trend across the latest:

```text
10 reviews
```

using a lightweight CSS sparkline.

No additional charting library is required for this visualization.

---

# 🗂️ Project History

The application provides project-level history for:

* Code Reviews
* Generated Tests
* Documentation

List endpoints return lightweight records while detail endpoints provide the complete content.

This keeps normal list responses smaller and more efficient.

---

# 🔔 UI Notifications

Phase 10 introduced a shared toast system.

The application provides:

```javascript
useToast().success()
useToast().error()
useToast().info()
```

Toasts are:

* Small
* Stacked
* Auto-dismissing
* Displayed in the bottom-right corner

Inline validation remains available for field-specific problems because it provides more useful feedback when the user needs to correct a particular field.

---

# ⌘ Command Palette

Press:

```text
Ctrl + K
```

on Windows/Linux or:

```text
Cmd + K
```

on macOS.

The command palette allows users to:

* Search projects
* Navigate to projects
* Create a project when no match exists

The current implementation is intentionally focused on project-level actions.

A future extension could provide a project-scoped:

```text
Ctrl/Cmd + P
```

quick-open file system.

---

# 🛡️ Security Hardening

Phase 11 introduced targeted security hardening based on an actual application audit.

## CSRF Protection

The React frontend uses a double-submit cookie strategy.

After login, the server sets:

```text
csrf_token
```

The frontend reads the token and sends it through:

```http
X-CSRF-Token: <token>
```

for authenticated state-changing API requests.

Protected methods include:

```text
POST
PUT
PATCH
DELETE
```

The server compares the cookie and header using constant-time comparison.

Authentication endpoints that operate before an authenticated session exists are exempt.

---

# 📂 File & Path Validation

File creation and rename operations validate:

* File extensions
* Filenames
* Folder paths
* Null bytes
* Path traversal
* Path separators

Dangerous values such as:

```text
../evil.py
```

are rejected.

The configured file-extension allowlist is also enforced.

Extensionless files that are intentionally supported, such as:

```text
Dockerfile
Makefile
README
```

can be handled through the explicit extensionless-name allowlist.

---

# 🚦 Rate Limiting

Rate limiting is applied to sensitive and expensive operations.

This includes areas such as:

* Login
* Registration
* Password recovery
* Email verification
* AI operations

Cheap authenticated CRUD operations are not unnecessarily rate-limited when the associated risk does not justify it.

---

# 🔒 Session Security

Flask's signed session cookies protect the authentication state.

The test suite also verifies that a corrupted or tampered session cookie results in:

```text
401 Unauthorized
```

rather than an application crash or accidental authentication.

---

# 🧪 Defensive AI Response Parsing

AI models do not always follow requested output formats perfectly.

The application therefore never blindly trusts AI-generated JSON.

Responses are parsed defensively with fallback behavior.

For example:

```text
Expected JSON
     ↓
Parse
     │
     ├── Valid → Use structured result
     │
     └── Invalid → Best-effort fallback
```

This prevents malformed AI output from unnecessarily becoming a server error.

---

# 🏗️ Architecture

The project uses a unified repository layout rather than separate top-level `frontend/` and `backend/` wrapper folders.

```text
ai-coding-assistant/
│
├── src/                              # React + Vite + Tailwind
│   ├── main.jsx
│   ├── App.jsx
│   ├── index.css
│   │
│   ├── assets/
│   ├── components/
│   │   ├── common/
│   │   ├── auth/
│   │   ├── chat/
│   │   ├── code/
│   │   └── analysis/
│   │
│   ├── pages/
│   │   ├── auth/
│   │   ├── Dashboard.jsx
│   │   └── ProjectWorkspace.jsx
│   │
│   ├── context/
│   ├── hooks/
│   ├── services/
│   │   └── api.js
│   └── utils/
│
├── server/                           # Flask backend
│   ├── app.py
│   ├── config.py
│   ├── extensions.py
│   │
│   ├── api/
│   │   ├── auth.py
│   │   ├── projects.py
│   │   ├── conversations.py
│   │   ├── ai.py
│   │   └── code.py
│   │
│   ├── models/
│   ├── services/
│   │   ├── auth/
│   │   ├── ai/
│   │   │   └── providers/
│   │   ├── chat/
│   │   ├── code/
│   │   └── projects/
│   │
│   ├── utils/
│   │   ├── ownership.py
│   │   ├── csrf.py
│   │   └── validation.py
│   │
│   ├── requirements.txt
│   └── tests/
│
├── data/
│   ├── database/
│   ├── uploads/
│   └── projects/
│
├── migrations/
├── scripts/
├── docs/
│   ├── architecture/
│   ├── api/
│   └── development/
│
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── index.html
│
├── app.py                             # Root launcher
├── .env.example
├── .gitignore
│
├── README.md
├── PRD.md
├── SECURITY.md
├── CONTRIBUTING.md
├── CHANGELOG.md
└── LICENSE
```

### Why This Structure?

The application keeps frontend and backend code in clearly organized directories while avoiding unnecessary wrapper layers such as:

```text
frontend/
backend/
```

Backend imports remain concise:

```python
from models.user import User
```

rather than deeply nested imports.

The root launcher provides a simple developer experience:

```bash
python app.py
```

---

# 🗄️ Data Layer

The backend uses SQLAlchemy with SQLite for local development.

The database is created automatically at:

```text
data/database/app.db
```

The data model includes entities for:

* Users
* Projects
* Project files
* Conversations
* Messages
* Code reviews
* Code analysis
* Generated tests
* Documentation
* Authentication-related records

Foreign keys, indexes, and cascading relationships are used where appropriate.

---

# 🔄 Application Flow

```text
                    ┌─────────────────┐
                    │     Browser     │
                    │ React + Monaco  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Flask API     │
                    │ Authentication  │
                    │   Validation    │
                    │   Rate Limit    │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
      ┌──────────┐    ┌────────────┐   ┌────────────┐
      │ Services │    │ AI Service │   │  Database  │
      └────┬─────┘    └─────┬──────┘   └────────────┘
           │                │
           │        ┌───────┼────────┐
           │        ▼       ▼        ▼
           │     Gemini   Groq   OpenRouter
           │
           ▼
      Business Logic
```

---

# ⚙️ Requirements

Before running the project, make sure you have:

* Python 3.11+
* Node.js
* npm
* Git

Check:

```bash
python --version
node --version
npm --version
```

---

# 🚀 Installation

Clone the repository:

```bash
git clone <your-repository-url>
cd ai-coding-assistant
```

Install backend dependencies:

```bash
pip install -r server/requirements.txt
```

Install frontend dependencies:

```bash
npm install
```

Create the environment file:

```text
.env.example → .env
```

Configure the required environment variables.

---

# ▶️ Running the Application

## Recommended — Single Command

From the project root:

```bash
python app.py
```

The root launcher can:

1. Check frontend dependencies.
2. Build the React application when required.
3. Start Flask.
4. Serve the API.
5. Serve the built React frontend.

The application is available at:

```text
http://localhost:5000
```

No separate frontend server is required for normal usage.

---

# ⚡ Frontend Development Mode

When actively developing the React interface, use Vite's hot reload.

### Terminal 1 — Backend

```bash
cd server
python app.py
```

### Terminal 2 — Frontend

From the project root:

```bash
npm run dev
```

Vite runs at:

```text
http://localhost:5173
```

and proxies API requests to Flask.

This mode provides immediate frontend updates without rebuilding the production bundle after every change.

---

# 🗃️ Database

The default development database is:

```text
data/database/app.db
```

It is created automatically.

The project currently uses SQLite for simplicity and local development.

A production deployment can later migrate to a dedicated relational database such as PostgreSQL.

---

# 🔑 Gemini Configuration

To enable real AI responses, configure at least:

```env
GEMINI_API_KEY_1=your-api-key
```

Additional keys can be configured:

```env
GEMINI_API_KEY_2=your-api-key
GEMINI_API_KEY_3=your-api-key
GEMINI_API_KEY_4=your-api-key
```

The provider configuration can be checked through:

```text
GET /api/ai/providers
```

The Gemini provider should report:

```json
{
  "configured": true
}
```

when a valid key is detected by the application configuration.

> Never commit API keys to Git.

---

# 📧 Email Development Mode

Email sending is suppressed by default for local development.

```env
MAIL_SUPPRESS_SEND=true
```

With this enabled, verification and password-reset links are logged to the backend console rather than sent through SMTP.

For actual email delivery, configure the required `MAIL_*` variables and disable suppression.

---

# 🧑‍💻 Trying the Application

## Authentication

1. Open `/register`.
2. Create an account.
3. Check the Flask console for the verification link.
4. Open the verification URL.
5. Log in.
6. Open the dashboard.

To test password recovery:

```text
/forgot-password
```

Then use the reset link printed by the development server.

---

# 📁 Trying Projects & Files

1. Log in.
2. Select **+ New Project**.
3. Open the project.
4. Select **+ New File**.
5. Enter a filename.
6. Optionally specify a folder such as:

   ```text
   src/utils
   ```
7. Edit the code.
8. Save using **Save** or:

   ```text
   Ctrl/Cmd + S
   ```

You can also:

* Rename files
* Delete files
* Rename folders
* Rename projects
* Delete projects
* Search projects

---

# 💬 Trying AI Chat

Configure:

```env
GEMINI_API_KEY_1=...
```

Then:

1. Open a project.
2. Create a new chat.
3. Ask a question.
4. Enable current-file context if required.
5. Select code in Monaco.
6. Use **Ask about selection →**.
7. Regenerate responses when needed.

Without an AI key, the application intentionally handles the provider failure path rather than crashing.

---

# 🧠 Trying Code Intelligence

Open a project and file, then select:

```text
Analyze ✨
```

Available actions include:

```text
Explain
Generate
Debug
Review
Optimize
Tests
Documentation
```

The AI operates on the current editor content, including unsaved changes.

---

# 🔀 Trying AI Diff Review

For actions such as:

* Optimize
* Debug
* Generate

the AI suggestion can be opened in the diff-review interface.

Review the proposed changes and choose:

```text
Accept
```

or:

```text
Reject
```

Accepting a change updates the draft but does not automatically save the file.

---

# 📊 Trying Code Analysis

Run a code review first.

Then open:

```text
📊 Code Analysis
```

The dashboard can display:

* Quality score
* Security score
* Performance score
* Maintainability score
* Complexity
* Issue counts
* Severity breakdown
* Review history
* Quality trend

---

# ⌘ Trying the Command Palette

Press:

```text
Ctrl + K
```

or:

```text
Cmd + K
```

Search for an existing project or enter a new project name to create one.

Use:

```text
↑ ↓
```

to navigate results and:

```text
Enter
```

to open or create the selected project.

---

# 🧪 Testing

Run the backend test suite:

```bash
cd server
python -m pytest tests/ -v
```

The current suite contains **135 tests** covering major application areas, including:

| Area                   |   Tests |
| ---------------------- | ------: |
| Authentication         |      17 |
| Multi-user isolation   |      20 |
| Projects/files/folders |      10 |
| AI provider layer      |      18 |
| AI chat                |      13 |
| Code intelligence      |      18 |
| Analysis/history       |       9 |
| CSRF                   |      10 |
| File/path validation   |      17 |
| Service-layer tests    |       3 |
| **Total**              | **135** |

The tests cover both happy paths and important failure/security scenarios.

---

# 🧪 Testing Philosophy

The test suite verifies more than whether endpoints return successful responses.

It also tests:

* Cross-user access attempts
* Ownership enforcement
* Missing resources
* Invalid inputs
* AI provider failures
* Malformed AI responses
* Session tampering
* CSRF protection
* File path traversal
* Invalid extensions
* API error handling
* Route protection
* Service-layer behavior

---

# 🔐 Security Considerations

The application implements several security controls, but it should **not** be considered production-security certified.

Current protections include:

* Session authentication
* Password hashing
* Signed tokens
* Token expiration
* Single-use reset/verification tokens
* Multi-user ownership enforcement
* CSRF protection
* Input validation
* Filename validation
* Path traversal protection
* API rate limiting
* Request validation
* Generic error responses
* Parameterized database queries
* Environment-based secrets
* No arbitrary code execution
* No arbitrary file uploads

See [`SECURITY.md`](SECURITY.md) for the security policy.

---

# ⚠️ Security Status

Security hardening is not something that can realistically be declared "finished."

Phase 11 addressed specific vulnerabilities and hardening gaps discovered during an application audit, including:

* Previously unused file-extension allowlist
* Missing CSRF protection
* Missing file/path validation
* Route protection verification
* Rate-limit coverage review
* Session-tampering test coverage

Further security work should include:

* Dependency vulnerability scanning
* Regular dependency updates
* Production secret management
* Professional penetration testing
* Infrastructure security review
* Deployment hardening
* Monitoring and alerting

These are outside the scope of a single development pass.

---

# 📈 Project Status

## Phase 0 — Scaffolding

✅ Completed

* Flask application
* React + Vite
* Tailwind CSS
* Environment configuration
* Development/test/production configuration

## Phase 1 — Data Layer

✅ Completed

* Database models
* Foreign keys
* Indexes
* Relationships
* Cascading deletes

## Phase 2 — Authentication

✅ Completed

* Registration
* Login/logout
* Email verification
* Password recovery
* Password reset
* Password change
* Password hashing
* Sessions
* Rate limiting

## Phase 3 — Multi-User Isolation

✅ Completed

* Centralized ownership enforcement
* Cross-user isolation
* Isolation tests
* Session-derived ownership

## Phase 4 — Project & File Management

✅ Completed

* Project CRUD
* File CRUD
* Virtual folders
* Search
* Workspace UI

## Phase 5 — Code Editor

✅ Completed

* Monaco Editor
* Language selection
* Formatting
* Copy
* Clear
* Save
* Keyboard shortcuts
* Dirty state

## Phase 6 — AI Architecture

✅ Completed

* AIService abstraction
* Gemini provider
* Gemini key rotation
* Provider stubs
* Provider discovery endpoint

## Phase 7 — AI Chat

✅ Completed

* Persistent conversations
* Message history
* Context selection
* Current-file context
* Selection context
* Auto-titling
* Regeneration
* Provider failure handling

## Phase 8 — Code Intelligence

✅ Completed

* Explain
* Generate
* Debug
* Review
* Optimize
* Tests
* Documentation

## Phase 9 — Diff & Analysis

✅ Completed

* Monaco Diff Editor
* Accept/reject workflow
* Code Analysis Dashboard
* Review history
* Generated test history
* Documentation history
* Quality trends

## Phase 10 — UI Polish

✅ Completed

* Toast notifications
* Shared loading states
* Shared empty states
* Command palette

## Phase 11 — Security Hardening

✅ Completed

* CSRF protection
* File-extension validation
* Filename validation
* Folder-path validation
* Path traversal protection
* Route security audit
* Rate-limit audit
* Session tampering test

---

# 🗺️ Future Roadmap

Although the original phased specification is complete, development can continue with additional improvements.

### AI Providers

* Complete Groq integration
* Complete OpenRouter integration
* Complete Claude integration
* Provider health monitoring
* Automatic provider fallback

### Developer Experience

* Quick file search
* `Ctrl/Cmd + P`
* Multi-file editing
* Workspace tabs
* Code autocomplete
* Improved syntax intelligence
* Keyboard shortcut customization

### AI Features

* Project-wide AI context
* Repository-aware search
* Embeddings
* RAG
* AI memory
* Agentic coding workflows
* Multi-file AI changes
* Automated refactoring

### Code Analysis

* Static analysis integration
* Security scanning
* Dependency analysis
* Code duplication detection
* Cyclomatic complexity analysis
* Technical debt tracking

### Production

* PostgreSQL support
* Redis integration
* Background task processing
* Production email service
* Containerization
* CI/CD
* Observability
* Monitoring
* Automated backups

---

# ⚠️ Current Limitations

The current implementation has several intentional limitations:

* Gemini is the primary implemented AI provider.
* Groq, OpenRouter, and Claude providers are currently stubs.
* Monaco normally requires browser access to load its runtime.
* SQLite is intended primarily for local development.
* AI responses are probabilistic and can contain incorrect suggestions.
* AI code fixes are not guaranteed to be correct.
* Code-analysis scores are AI-assisted estimates.
* No professional penetration test has been performed.
* Dependency vulnerability scanning is still an ongoing operational requirement.
* Production infrastructure hardening is outside the scope of the current project.

---

# 🏆 Project Goals

The project demonstrates how to build a complete AI-powered development platform while addressing both functionality and engineering concerns.

It combines:

```text
React
  +
Flask
  +
SQLAlchemy
  +
Monaco Editor
  +
Machine/AI Services
  +
Authentication
  +
Multi-user Isolation
  +
Security
  +
Testing
```

The goal is not simply to create an AI chatbot around a code editor.

The goal is to demonstrate a **structured, extensible development platform** where AI functionality is integrated into project management, code editing, code analysis, testing, documentation, and developer workflows.

---

# 🤝 Contributing

Contributions are welcome.

Before contributing, read:

* [`CONTRIBUTING.md`](CONTRIBUTING.md)
* [`SECURITY.md`](SECURITY.md)
* [`PRD.md`](PRD.md)

For security vulnerabilities, please follow the private reporting process described in `SECURITY.md` rather than opening a public issue.

---

# 📜 License

This project is licensed under the **MIT License**.

See [`LICENSE`](LICENSE) for details.

---

# 👨‍💻 Author

**Abaid-ur-Rehman**

AI / Machine Learning Engineer & Python Developer

Built as a portfolio-focused implementation of a complete AI-assisted software development environment.

---

# ⭐ Support the Project

If you find this project useful or interesting:

* ⭐ Star the repository
* 🍴 Fork the project
* 🐛 Report bugs
* 💡 Suggest improvements
* 🤝 Contribute
* 📚 Use it as a learning reference

---

<p align="center">

**AI Coding Assistant — Build smarter. Code faster.**

</p>
