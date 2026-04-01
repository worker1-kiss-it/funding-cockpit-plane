import { useState, useRef, useEffect, useCallback } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import { MessageSquare, X, Send, Bot, User } from "lucide-react";
import { useProject } from "@/hooks/store/use-project";
import { FundingService } from "@/services/funding.service";

const service = new FundingService();

export const FundingChat = observer(function FundingChat() {
  const { workspaceSlug } = useParams<{ workspaceSlug: string }>();
  const { workspaceProjectIds } = useProject();
  const projectId = workspaceProjectIds?.[0];

  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  useEffect(() => {
    if (isOpen && !historyLoaded && workspaceSlug && projectId) {
      service.getChatHistory(workspaceSlug, projectId)
        .then((data) => {
          setMessages(data?.messages || []);
          setHistoryLoaded(true);
        })
        .catch(() => {});
    }
  }, [isOpen, historyLoaded, workspaceSlug, projectId]);

  const sendMessage = async () => {
    if (!input.trim() || !workspaceSlug || !projectId || isLoading) return;
    const msg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setIsLoading(true);
    try {
      const data = await service.sendChatMessage(workspaceSlug, projectId, msg);
      setMessages((prev) => [...prev, { role: "assistant", content: data?.response || "No response." }]);
    } catch {
      setMessages((prev) => [...prev, { role: "system", content: "Failed to get response." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-[70] flex items-center justify-center size-12 rounded-full bg-custom-primary-100 text-white shadow-xl hover:opacity-90 transition-opacity"
      >
        {isOpen ? <X className="size-5" /> : <MessageSquare className="size-5" />}
      </button>

      {/* Chat Drawer Panel */}
      {isOpen && (
        <div
          className="fixed right-0 top-0 h-full w-96 z-[60] flex flex-col shadow-2xl border-l-2"
          style={{
            backgroundColor: "var(--color-bg-base, #1f2937)",
            borderColor: "var(--color-border-subtle, #374151)",
            color: "var(--color-text-base, #e5e7eb)",
          }}
        >
          {/* Header */}
          <div
            className="flex items-center justify-between px-4 py-3 border-b-2"
            style={{ borderColor: "var(--color-border-subtle, #374151)" }}
          >
            <div className="flex items-center gap-2">
              <Bot className="size-5 text-custom-primary-100" />
              <h3 className="font-semibold text-base">AI Assistant</h3>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="opacity-60 hover:opacity-100 transition-opacity"
            >
              <X className="size-4" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-12 opacity-50 text-sm">
                <Bot className="size-8 mx-auto mb-3 opacity-30" />
                <p>Ask me anything about your funding opportunities.</p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-2.5 ${msg.role === "user" ? "justify-end" : ""}`}>
                {msg.role !== "user" && (
                  <div className="flex-shrink-0 size-6 rounded-full bg-custom-primary-100/15 flex items-center justify-center mt-0.5">
                    <Bot className="size-3.5 text-custom-primary-100" />
                  </div>
                )}
                <div
                  className={`rounded-lg px-3.5 py-2.5 text-sm max-w-[80%] leading-relaxed ${
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
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                </div>
                {msg.role === "user" && (
                  <div className="flex-shrink-0 size-6 rounded-full bg-custom-primary-100/20 flex items-center justify-center mt-0.5">
                    <User className="size-3.5 text-custom-primary-100" />
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="flex gap-2.5">
                <div className="flex-shrink-0 size-6 rounded-full bg-custom-primary-100/15 flex items-center justify-center mt-0.5">
                  <Bot className="size-3.5 text-custom-primary-100" />
                </div>
                <div
                  className="rounded-lg px-3.5 py-2.5 text-sm"
                  style={{ backgroundColor: "var(--color-bg-subtle, #374151)", border: "1px solid var(--color-border-subtle, #4b5563)" }}
                >
                  <div className="flex items-center gap-1.5 opacity-50">
                    <div className="size-1.5 rounded-full bg-current animate-pulse" />
                    <div className="size-1.5 rounded-full bg-current animate-pulse [animation-delay:0.2s]" />
                    <div className="size-1.5 rounded-full bg-current animate-pulse [animation-delay:0.4s]" />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div
            className="p-3 border-t-2"
            style={{ borderColor: "var(--color-border-subtle, #374151)" }}
          >
            <div className="flex items-center gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                placeholder="Type a message..."
                className="flex-1 rounded-lg px-3.5 py-2 text-sm outline-none placeholder:opacity-40"
                style={{
                  backgroundColor: "var(--color-bg-subtle, #374151)",
                  border: "1px solid var(--color-border-subtle, #4b5563)",
                  color: "inherit",
                }}
                disabled={isLoading}
              />
              <button
                onClick={sendMessage}
                disabled={isLoading || !input.trim()}
                className="p-2 rounded-lg bg-custom-primary-100 text-white disabled:opacity-40 hover:opacity-90 transition-opacity"
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
