import { useState, useRef, useEffect, useCallback } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import ReactMarkdown from "react-markdown";
import { MessageSquare, X, Send, Bot, User, Plus, History } from "lucide-react";
import { useProject } from "@/hooks/store/use-project";
import { FundingService } from "@/services/funding.service";

const service = new FundingService();

type Role = "user" | "assistant" | "system" | "tool";
type Message = {
  id?: string;
  role: Role;
  content: string;
  tokens_in?: number | null;
  tokens_out?: number | null;
  cost_usd?: number | null;
  streaming?: boolean;
};
type Session = {
  id: string;
  claude_session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export const FundingChat = observer(function FundingChat() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();
  const { workspaceProjectIds } = useProject();
  const projectId = workspaceProjectIds?.[0];

  const [isOpen, setIsOpen] = useState(false);
  const [showSessions, setShowSessions] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  const loadSessions = useCallback(async () => {
    if (!workspaceSlug || !projectId) return;
    try {
      const data = await service.listChatSessions(workspaceSlug, projectId);
      setSessions(data?.sessions || []);
    } catch {
      /* ignore */
    }
  }, [workspaceSlug, projectId]);

  useEffect(() => {
    if (isOpen) void loadSessions();
  }, [isOpen, loadSessions]);

  const ensureSession = useCallback(async (): Promise<string | null> => {
    if (activeSessionId) return activeSessionId;
    if (!workspaceSlug || !projectId) return null;
    const session = await service.createChatSession(workspaceSlug, projectId);
    setSessions((s) => [session, ...s]);
    setActiveSessionId(session.id);
    setMessages([]);
    return session.id;
  }, [activeSessionId, workspaceSlug, projectId]);

  const newSession = useCallback(async () => {
    if (!workspaceSlug || !projectId) return;
    const session = await service.createChatSession(workspaceSlug, projectId);
    setSessions((s) => [session, ...s]);
    setActiveSessionId(session.id);
    setMessages([]);
    setShowSessions(false);
  }, [workspaceSlug, projectId]);

  const pickSession = useCallback(
    async (id: string) => {
      if (!workspaceSlug || !projectId) return;
      setActiveSessionId(id);
      setShowSessions(false);
      try {
        const data = await service.listChatMessages(workspaceSlug, projectId, id);
        setMessages(data?.messages || []);
      } catch {
        setMessages([]);
      }
    },
    [workspaceSlug, projectId]
  );

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || !workspaceSlug || !projectId || isStreaming) return;
    setInput("");
    const sessionId = await ensureSession();
    if (!sessionId) return;

    setMessages((m) => [...m, { role: "user", content: text }, { role: "assistant", content: "", streaming: true }]);
    setIsStreaming(true);

    try {
      await service.streamChatMessage(workspaceSlug, projectId, sessionId, text, (event: any) => {
        setMessages((curr) => {
          const copy = curr.slice();
          const last = copy[copy.length - 1];
          if (!last || last.role !== "assistant") return curr;
          if (event.type === "delta" && typeof event.text === "string") {
            copy[copy.length - 1] = { ...last, content: last.content + event.text };
          } else if (event.type === "done") {
            copy[copy.length - 1] = {
              ...last,
              streaming: false,
              id: event.message_id,
              tokens_in: event.tokens_in ?? null,
              tokens_out: event.tokens_out ?? null,
              cost_usd: event.cost_usd ?? null,
            };
          } else if (event.type === "error") {
            copy[copy.length - 1] = { role: "system", content: event.message || "error", streaming: false };
          }
          return copy;
        });
      });
    } catch (e: any) {
      setMessages((curr) => {
        const copy = curr.slice();
        copy[copy.length - 1] = { role: "system", content: e?.message || "Failed to reach the assistant" };
        return copy;
      });
    } finally {
      setIsStreaming(false);
      void loadSessions();
    }
  }, [input, workspaceSlug, projectId, isStreaming, ensureSession, loadSessions]);

  return (
    <>
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="bg-custom-primary-100 shadow-xl fixed right-6 bottom-6 z-[70] flex size-12 items-center justify-center rounded-full text-white transition-opacity hover:opacity-90"
      >
        {isOpen ? <X className="size-5" /> : <MessageSquare className="size-5" />}
      </button>

      {isOpen && (
        <div
          className="shadow-2xl fixed top-0 right-0 z-[60] flex h-full w-[28rem] flex-col border-l-2"
          style={{
            backgroundColor: "var(--color-bg-base, #1f2937)",
            borderColor: "var(--color-border-subtle, #374151)",
            color: "var(--color-text-base, #e5e7eb)",
          }}
        >
          <div
            className="flex items-center justify-between border-b-2 px-4 py-3"
            style={{ borderColor: "var(--color-border-subtle, #374151)" }}
          >
            <div className="flex items-center gap-2">
              <Bot className="text-custom-primary-100 size-5" />
              <h3 className="text-base font-semibold">Funding Assistant</h3>
            </div>
            <div className="flex items-center gap-2">
              <button
                title="Conversations"
                onClick={() => setShowSessions((v) => !v)}
                className="opacity-60 hover:opacity-100"
              >
                <History className="size-4" />
              </button>
              <button title="New chat" onClick={newSession} className="opacity-60 hover:opacity-100">
                <Plus className="size-4" />
              </button>
              <button onClick={() => setIsOpen(false)} className="opacity-60 hover:opacity-100">
                <X className="size-4" />
              </button>
            </div>
          </div>

          {showSessions && (
            <div
              className="max-h-60 overflow-auto border-b-2 p-2"
              style={{ borderColor: "var(--color-border-subtle, #374151)" }}
            >
              {sessions.length === 0 && <div className="text-xs px-2 py-1 opacity-60">No previous conversations.</div>}
              {sessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => pickSession(s.id)}
                  className={`text-xs w-full rounded px-2 py-1.5 text-left hover:bg-white/5 ${
                    s.id === activeSessionId ? "bg-white/10" : ""
                  }`}
                >
                  <div className="truncate font-medium">{s.title || "Untitled"}</div>
                  <div className="opacity-50">{new Date(s.updated_at).toLocaleString()}</div>
                </button>
              ))}
            </div>
          )}

          <div className="flex-1 space-y-4 overflow-auto p-4">
            {messages.length === 0 && !isStreaming && (
              <div className="text-sm py-12 text-center opacity-50">
                <Bot className="mx-auto mb-3 size-8 opacity-30" />
                <p>Ask anything about your funding pipeline.</p>
              </div>
            )}
            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-2.5 ${msg.role === "user" ? "justify-end" : ""}`}>
                {msg.role !== "user" && (
                  <div className="bg-custom-primary-100/15 mt-0.5 flex size-6 flex-shrink-0 items-center justify-center rounded-full">
                    <Bot className="text-custom-primary-100 size-3.5" />
                  </div>
                )}
                <div
                  className={`text-sm max-w-[80%] rounded-lg px-3.5 py-2.5 leading-relaxed ${
                    msg.role === "user"
                      ? "bg-custom-primary-100 text-white"
                      : msg.role === "system"
                        ? "text-red-400"
                        : ""
                  }`}
                  style={
                    msg.role !== "user" && msg.role !== "system"
                      ? {
                          backgroundColor: "var(--color-bg-subtle, #374151)",
                          border: "1px solid var(--color-border-subtle, #4b5563)",
                        }
                      : msg.role === "system"
                        ? { backgroundColor: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.2)" }
                        : undefined
                  }
                >
                  {msg.role === "assistant" ? (
                    <div className="prose-sm prose-invert max-w-none prose">
                      <ReactMarkdown>{msg.content || (msg.streaming ? "…" : "")}</ReactMarkdown>
                    </div>
                  ) : (
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  )}
                  {msg.role === "assistant" && !msg.streaming && (msg.tokens_out || msg.cost_usd) ? (
                    <div className="mt-1.5 text-[10px] opacity-40">
                      {msg.tokens_in ?? "?"} in / {msg.tokens_out ?? "?"} out
                      {msg.cost_usd != null ? ` · $${msg.cost_usd.toFixed(4)}` : null}
                    </div>
                  ) : null}
                </div>
                {msg.role === "user" && (
                  <div className="bg-custom-primary-100/20 mt-0.5 flex size-6 flex-shrink-0 items-center justify-center rounded-full">
                    <User className="text-custom-primary-100 size-3.5" />
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          <div className="border-t-2 p-3" style={{ borderColor: "var(--color-border-subtle, #374151)" }}>
            <div className="flex items-center gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void send();
                  }
                }}
                placeholder="Ask the assistant…"
                className="text-sm flex-1 rounded-lg px-3.5 py-2 outline-none placeholder:opacity-40"
                style={{
                  backgroundColor: "var(--color-bg-subtle, #374151)",
                  border: "1px solid var(--color-border-subtle, #4b5563)",
                  color: "inherit",
                }}
                disabled={isStreaming}
              />
              <button
                onClick={send}
                disabled={isStreaming || !input.trim()}
                className="bg-custom-primary-100 rounded-lg p-2 text-white hover:opacity-90 disabled:opacity-40"
              >
                <Send className="size-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
});
