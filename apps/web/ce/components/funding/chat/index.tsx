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
        className="fixed bottom-6 right-6 z-50 flex items-center justify-center size-12 rounded-full bg-custom-primary-100 text-white shadow-lg hover:opacity-90 transition-opacity"
      >
        {isOpen ? <X className="size-5" /> : <MessageSquare className="size-5" />}
      </button>

      {/* Chat Drawer */}
      {isOpen && (
        <div className="fixed right-0 top-0 h-full w-96 z-[60] border-l shadow-2xl flex flex-col" style={{ backgroundColor: "rgb(var(--color-background-100, 255 255 255))", borderColor: "rgb(var(--color-border-200, 229 231 235))" }}>
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: "rgb(var(--color-border-200, 229 231 235))" }}>
            <div className="flex items-center gap-2">
              <Bot className="size-5 text-custom-primary-100" />
              <h3 className="font-medium text-custom-text-100">AI Assistant</h3>
            </div>
            <button onClick={() => setIsOpen(false)} className="text-custom-text-300 hover:text-custom-text-100">
              <X className="size-4" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-auto p-4 space-y-4" style={{ backgroundColor: "rgb(var(--color-background-100, 255 255 255))" }}>
            {messages.length === 0 && (
              <div className="text-center py-12 text-custom-text-300 text-sm">
                <Bot className="size-8 mx-auto mb-3 opacity-30" />
                <p>Ask me anything about your funding opportunities.</p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-2 ${msg.role === "user" ? "justify-end" : ""}`}>
                {msg.role !== "user" && (
                  <Bot className="size-5 shrink-0 mt-0.5 text-custom-primary-100" />
                )}
                <div className={`rounded-lg px-3 py-2 text-sm max-w-[80%] ${
                  msg.role === "user"
                    ? "bg-custom-primary-100 text-white"
                    : msg.role === "system"
                    ? "bg-red-500/10 text-red-500"
                    : "text-custom-text-100"
                }`} style={msg.role !== "user" && msg.role !== "system" ? { backgroundColor: "rgb(var(--color-background-90, 243 244 246))" } : undefined}>
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                </div>
                {msg.role === "user" && (
                  <User className="size-5 shrink-0 mt-0.5 text-custom-text-300" />
                )}
              </div>
            ))}
            {isLoading && (
              <div className="flex gap-2">
                <Bot className="size-5 shrink-0 mt-0.5 text-custom-primary-100" />
                <div className="bg-custom-background-90 rounded-lg px-3 py-2 text-sm text-custom-text-300">
                  Thinking...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t" style={{ borderColor: "rgb(var(--color-border-200, 229 231 235))", backgroundColor: "rgb(var(--color-background-100, 255 255 255))" }}>
            <div className="flex items-center gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                placeholder="Type a message..."
                className="flex-1 rounded-md px-3 py-2 text-sm outline-none text-custom-text-100 placeholder:text-custom-text-400"
                style={{ backgroundColor: "rgb(var(--color-background-90, 243 244 246))" }}
                disabled={isLoading}
              />
              <button
                onClick={sendMessage}
                disabled={isLoading || !input.trim()}
                className="p-2 rounded-md bg-custom-primary-100 text-white disabled:opacity-50 hover:opacity-90"
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
