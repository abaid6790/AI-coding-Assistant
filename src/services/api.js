const BASE_URL = "/api";
const CSRF_COOKIE_NAME = "csrf_token";
const CSRF_HEADER_NAME = "X-CSRF-Token";
const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

class ApiError extends Error {
  constructor(message, status, fieldErrors) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors || null;
  }
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function request(path, { method = "GET", body, ...rest } = {}) {
  const headers = body ? { "Content-Type": "application/json" } : {};

  // The backend requires this header (matched against a same-named,
  // readable cookie set at login) on authenticated mutating requests —
  // see server/utils/csrf.py. A cross-site page can't read our cookie
  // to construct a matching header, so this is real CSRF protection,
  // not just a formality — every write has to carry it.
  if (MUTATING_METHODS.has(method.toUpperCase())) {
    const token = getCookie(CSRF_COOKIE_NAME);
    if (token) headers[CSRF_HEADER_NAME] = token;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    credentials: "include", // send the session cookie
    headers,
    body: body ? JSON.stringify(body) : undefined,
    ...rest,
  });

  const isJson = res.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await res.json() : null;

  if (!res.ok) {
    throw new ApiError(data?.error || "Request failed.", res.status, data?.field_errors);
  }
  return data;
}

export const api = {
  register: (payload) => request("/auth/register", { method: "POST", body: payload }),
  login: (payload) => request("/auth/login", { method: "POST", body: payload }),
  logout: () => request("/auth/logout", { method: "POST" }),
  me: () => request("/auth/me"),
  verifyEmail: (token) => request("/auth/verify-email", { method: "POST", body: { token } }),
  resendVerification: (email) => request("/auth/resend-verification", { method: "POST", body: { email } }),
  forgotPassword: (email) => request("/auth/forgot-password", { method: "POST", body: { email } }),
  resetPassword: (token, password) =>
    request("/auth/reset-password", { method: "POST", body: { token, password } }),
  changePassword: (current_password, new_password) =>
    request("/auth/change-password", { method: "POST", body: { current_password, new_password } }),

  // Projects
  listProjects: (search) => request(`/projects${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createProject: (payload) => request("/projects", { method: "POST", body: payload }),
  getProject: (id) => request(`/projects/${id}`),
  updateProject: (id, payload) => request(`/projects/${id}`, { method: "PATCH", body: payload }),
  deleteProject: (id) => request(`/projects/${id}`, { method: "DELETE" }),

  // Files
  listFiles: (projectId, search) =>
    request(`/projects/${projectId}/files${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createFile: (projectId, payload) =>
    request(`/projects/${projectId}/files`, { method: "POST", body: payload }),
  getFile: (projectId, fileId) => request(`/projects/${projectId}/files/${fileId}`),
  updateFile: (projectId, fileId, payload) =>
    request(`/projects/${projectId}/files/${fileId}`, { method: "PATCH", body: payload }),
  deleteFile: (projectId, fileId) =>
    request(`/projects/${projectId}/files/${fileId}`, { method: "DELETE" }),

  // Folders
  listFolders: (projectId) => request(`/projects/${projectId}/folders`),
  renameFolder: (projectId, oldPath, newPath) =>
    request(`/projects/${projectId}/folders`, {
      method: "PATCH",
      body: { old_path: oldPath, new_path: newPath },
    }),

  // AI providers (Phase 6 — status only; chat/generation lands in Phase 7+)
  listAiProviders: () => request("/ai/providers"),

  // Conversations & chat (Phase 7)
  listConversations: (projectId) =>
    request(`/conversations${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ""}`),
  createConversation: (payload) => request("/conversations", { method: "POST", body: payload }),
  getConversation: (id) => request(`/conversations/${id}`),
  renameConversation: (id, title) => request(`/conversations/${id}`, { method: "PATCH", body: { title } }),
  deleteConversation: (id) => request(`/conversations/${id}`, { method: "DELETE" }),
  sendMessage: (conversationId, payload) =>
    request(`/conversations/${conversationId}/messages`, { method: "POST", body: payload }),
  regenerateMessage: (conversationId, messageId, payload = {}) =>
    request(`/conversations/${conversationId}/messages/${messageId}/regenerate`, {
      method: "POST",
      body: payload,
    }),

  // Code intelligence (Phase 8)
  explainCode: (payload) => request("/code/explain", { method: "POST", body: payload }),
  generateCode: (payload) => request("/code/generate", { method: "POST", body: payload }),
  debugCode: (payload) => request("/code/debug", { method: "POST", body: payload }),
  reviewCode: (payload) => request("/code/review", { method: "POST", body: payload }),
  optimizeCode: (payload) => request("/code/optimize", { method: "POST", body: payload }),
  generateTestsForCode: (payload) => request("/code/tests", { method: "POST", body: payload }),
  generateDocumentation: (payload) => request("/code/documentation", { method: "POST", body: payload }),

  // Run Code (Phase 13) — a 200 response can still mean the CODE
  // failed (success: false in the body); request() only throws for a
  // genuine HTTP-level failure (missing code, unsupported language,
  // auth, rate limit).
  runCode: (payload) => request("/code/run", { method: "POST", body: payload }),

  // Code-intelligence history & analysis dashboard (Phase 9)
  getProjectAnalysis: (projectId) => request(`/projects/${projectId}/analysis`),
  listProjectReviews: (projectId) => request(`/projects/${projectId}/reviews`),
  listProjectTests: (projectId) => request(`/projects/${projectId}/tests`),
  getProjectTest: (projectId, testId) => request(`/projects/${projectId}/tests/${testId}`),
  listProjectDocuments: (projectId) => request(`/projects/${projectId}/documents`),
  getProjectDocument: (projectId, documentId) => request(`/projects/${projectId}/documents/${documentId}`),
};

export { ApiError };
