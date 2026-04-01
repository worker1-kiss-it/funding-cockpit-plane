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

      {/* Chat Drawer - uses surface-1 (different plane, like a modal) */}
      {isOpen && (
        <div className="fixed right-0 top-0 h-full w-96 z-[60] bg-surface-1 border-l border-subtle shadow-2xl flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-subtle">
            <div className="flex items-center gap-2">
              <Bot className="size-5 text-custom-primary-100" />
              <h3 className="font-medium text-base">AI Assistant</h3>
            </div>
            <button onClick={() => setIsOpen(false)} className="text-foreground-3 hover:text-foreground-1 transition-colors">
              <X className="size-4" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-12 text-foreground-3 text-sm">
                <Bot className="size-8 mx-auto mb-3 opacity-30" />
                <p>Ask me anything about your funding opportunities.</p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-2.5 ${msg.role === "user" ? "justify-end" : ""}`}>
                {msg.role !== "user" && (
                  <div className="flex-shrink-0 size-6 rounded-full bg-custom-primary-100/10 flex items-center justify-center mt-0.5">
                    <Bot className="size-3.5 text-custom-primary-100" />
                  </div>
                )}
                <div className={`rounded-lg px-3.5 py-2.5 text-sm max-w-[80%] leading-relaxed ${
                  msg.role === "user"
                    ? "bg-custom-primary-100 text-white"
                    : msg.role === "system"
                    ? "bg-red-500/10 text-red-400 border border-red-500/20"
                    : "bg-layer-1 border border-subtle"
                }`}>
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
                <div className="flex-shrink-0 size-6 rounded-full bg-custom-primary-100/10 flex items-center justify-center mt-0.5">
                  <Bot className="size-3.5 text-custom-primary-100" />
                </div>
                <div className="bg-layer-1 border border-subtle rounded-lg px-3.5 py-2.5 text-sm">
                  <div className="flex items-center gap-1.5 text-foreground-3">
                    <div className="size-1.5 rounded-full bg-foreground-3 animate-pulse" />
                    <div className="size-1.5 rounded-full bg-foreground-3 animate-pulse [animation-delay:0.2s]" />
                    <div className="size-1.5 rounded-full bg-foreground-3 animate-pulse [animation-delay:0.4s]" />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t border-subtle">
            <div className="flex items-center gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                placeholder="Type a message..."
                className="flex-1 bg-layer-1 border border-subtle rounded-lg px-3.5 py-2 text-sm outline-none focus:border-custom-primary-100 transition-colors placeholder:text-foreground-4"
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
