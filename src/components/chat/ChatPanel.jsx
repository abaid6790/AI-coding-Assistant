import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../../services/api.js";
import ChatMessageContent from "./ChatMessageContent.jsx";
import Spinner from "../common/Spinner.jsx";
import { inputClass } from "../auth/AuthShell.jsx";

export default function ChatPanel({ projectId, activeFile, pendingSelection, onConsumeSelection }) {
  const [conversations, setConversations] = useState([]);
  const [activeConvo, setActiveConvo] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingThread, setLoadingThread] = useState(false);
  const [sending, setSending] = useState(false);
  const [regeneratingId, setRegeneratingId] = useState(null);
  const [draft, setDraft] = useState("");
  const [attachFile, setAttachFile] = useState(true);
  const [error, setError] = useState("");
  const scrollRef = useRef(null);

  const loadConversations = async () => {
    setLoadingList(true);
    try {
      const data = await api.listConversations(projectId);
      setConversations(data.conversations);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load conversations.");
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    loadConversations();
    setActiveConvo(null);
    setMessages([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // If the editor sends a selection over while no conversation is open,
  // start a new one automatically — "start a conversation from selected code".
  useEffect(() => {
    if (pendingSelection && !activeConvo) {
      handleNewConversation();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingSelection]);

  const openConversation = async (summary) => {
    setLoadingThread(true);
    setError("");
    try {
      const data = await api.getConversation(summary.id);
      setActiveConvo(data.conversation);
      setMessages(data.messages);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not open conversation.");
    } finally {
      setLoadingThread(false);
    }
  };

  const handleNewConversation = async () => {
    try {
      const data = await api.createConversation({ project_id: projectId });
      setActiveConvo(data.conversation);
      setMessages([]);
      setConversations((prev) => [data.conversation, ...prev]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start a new conversation.");
    }
  };

  const handleDeleteConversation = async (id) => {
    if (!window.confirm("Delete this conversation?")) return;
    try {
      await api.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConvo?.id === id) {
        setActiveConvo(null);
        setMessages([]);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete conversation.");
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!draft.trim() || !activeConvo) return;

    setSending(true);
    setError("");
    const payload = { content: draft };
    if (attachFile && activeFile) payload.file_id = activeFile.id;
    if (pendingSelection) {
      payload.selection = pendingSelection;
      onConsumeSelection?.();
    }

    try {
      const data = await api.sendMessage(activeConvo.id, payload);
      setMessages((prev) => [...prev, data.user_message, data.assistant_message]);
      setActiveConvo(data.conversation);
      setConversations((prev) =>
        prev.map((c) => (c.id === data.conversation.id ? data.conversation : c))
      );
      setDraft("");
    } catch (err) {
      if (err instanceof ApiError && err.status && err.status >= 500) {
        // The user's message was still persisted server-side even
        // though the AI call failed — reflect that in the thread.
        setMessages((prev) => [...prev, { id: `local-${Date.now()}`, role: "user", content: draft }]);
        setDraft("");
      }
      setError(err instanceof ApiError ? err.message : "Could not send message.");
    } finally {
      setSending(false);
    }
  };

  const handleRegenerate = async (messageId) => {
    if (!activeConvo) return;
    setRegeneratingId(messageId);
    setError("");
    try {
      const data = await api.regenerateMessage(activeConvo.id, messageId);
      setMessages((prev) => prev.map((m) => (m.id === messageId ? data.assistant_message : m)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not regenerate that response.");
    } finally {
      setRegeneratingId(null);
    }
  };

  return (
    <div className="flex h-full flex-col border-l border-surface-700 bg-surface-900">
      <div className="flex items-center justify-between border-b border-surface-800 px-3 py-2">
        <span className="text-xs font-medium text-gray-400">AI Chat</span>
        <button onClick={handleNewConversation} className="text-xs text-accent-500 hover:underline">
          + New chat
        </button>
      </div>

      {!activeConvo ? (
        <div className="flex-1 overflow-y-auto p-2">
          {loadingList ? (
            <div className="p-2"><Spinner label="Loading…" /></div>
          ) : conversations.length === 0 ? (
            <p className="p-3 text-xs text-gray-500">No conversations yet for this project.</p>
          ) : (
            conversations.map((c) => (
              <div key={c.id} className="group flex items-center justify-between rounded px-2 py-1.5 hover:bg-surface-800">
                <button onClick={() => openConversation(c)} className="flex-1 truncate text-left text-xs text-gray-300">
                  {c.title}
                </button>
                <button
                  onClick={() => handleDeleteConversation(c.id)}
                  className="hidden text-xs text-gray-600 hover:text-red-400 group-hover:block"
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between border-b border-surface-800 px-3 py-1.5">
            <button onClick={() => setActiveConvo(null)} className="text-xs text-gray-500 hover:text-gray-300">
              ← All chats
            </button>
            <span className="truncate text-xs text-gray-400">{activeConvo.title}</span>
          </div>

          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-3">
            {loadingThread ? (
              <Spinner label="Loading…" />
            ) : messages.length === 0 ? (
              <p className="text-xs text-gray-500">Ask anything about your code.</p>
            ) : (
              messages.map((m) => (
                <div key={m.id} className={m.role === "user" ? "ml-6" : "mr-2"}>
                  <div
                    className={`rounded-lg px-3 py-2 ${
                      m.role === "user" ? "bg-accent-600/20" : "bg-surface-800"
                    }`}
                  >
                    <ChatMessageContent content={m.content} />
                  </div>
                  {m.role === "assistant" && !String(m.id).startsWith("local-") && (
                    <button
                      onClick={() => handleRegenerate(m.id)}
                      disabled={regeneratingId === m.id}
                      className="mt-1 text-[10px] text-gray-500 hover:text-accent-500 disabled:opacity-50"
                    >
                      {regeneratingId === m.id ? "Regenerating…" : "↻ Regenerate"}
                    </button>
                  )}
                </div>
              ))
            )}
          </div>

          {pendingSelection && (
            <div className="mx-3 mb-1 flex items-center justify-between rounded-md border border-accent-500/30 bg-accent-500/10 px-2 py-1 text-[11px] text-accent-300">
              <span>Attached: selected code ({pendingSelection.length} chars)</span>
              <button onClick={() => onConsumeSelection?.()} className="text-accent-400 hover:text-accent-200">
                ✕
              </button>
            </div>
          )}

          {error && <p className="mx-3 mb-1 text-[11px] text-red-400">{error}</p>}

          <form onSubmit={handleSend} className="border-t border-surface-800 p-2">
            {activeFile && (
              <label className="mb-1.5 flex items-center gap-1.5 text-[11px] text-gray-500">
                <input
                  type="checkbox"
                  checked={attachFile}
                  onChange={(e) => setAttachFile(e.target.checked)}
                  className="h-3 w-3"
                />
                Include current file ({activeFile.filename}) as context
              </label>
            )}
            <div className="flex gap-2">
              <input
                className={`${inputClass} text-xs`}
                placeholder="Ask about your code…"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                disabled={sending}
              />
              <button
                type="submit"
                disabled={sending || !draft.trim()}
                className="rounded-md bg-accent-600 px-3 py-2 text-xs font-medium text-white hover:bg-accent-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {sending ? "…" : "Send"}
              </button>
            </div>
          </form>
        </>
      )}
    </div>
  );
}
