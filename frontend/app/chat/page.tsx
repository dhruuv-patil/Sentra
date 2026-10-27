"use client";

import React, { useState, useRef, useEffect } from "react";
import { AppShell } from "@/components/layout/app-shell";
import {
  MessageSquare,
  Send,
  ShieldCheck,
  Bot,
  User,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  securityMeta?: {
    risk_score?: number;
    latency?: number;
    tokens?: number;
    cache_hit?: boolean;
    blocked?: boolean;
    reason?: string;
  };
}

export default function ChatPage() {
  const [model, setModel] = useState("groq/llama-3.3-70b-versatile");
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "init_1",
      role: "system",
      content:
        "LLM Security Gateway Pro connected. Zero-trust prompt interception, PII redaction, and output leakage monitoring active.",
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput("");

    const userMsg: Message = {
      id: `usr_${Date.now()}`,
      role: "user",
      content: userText,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const startTime = performance.now();
      const res = await fetch("/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model,
          messages: [
            ...messages.filter((m) => m.role !== "system").map((m) => ({
              role: m.role,
              content: m.content,
            })),
            { role: "user", content: userText },
          ],
        }),
      });

      const elapsed = Math.round(performance.now() - startTime);

      if (res.status === 403) {
        const errData = await res.json();
        const blockMsg: Message = {
          id: `block_${Date.now()}`,
          role: "assistant",
          content: `Security Block: ${errData.error || errData.detail || "Adversarial payload blocked by security policy."}`,
          timestamp: new Date().toLocaleTimeString(),
          securityMeta: {
            blocked: true,
            risk_score: 95,
            latency: elapsed,
            reason: errData.error || errData.detail,
          },
        };
        setMessages((prev) => [...prev, blockMsg]);
        toast.error("Message blocked by security guardrail.");
      } else if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText);
      } else {
        const data = await res.json();
        const assistantText =
          data.choices?.[0]?.message?.content || "No completion returned.";
        const assistantMsg: Message = {
          id: `ast_${Date.now()}`,
          role: "assistant",
          content: assistantText,
          timestamp: new Date().toLocaleTimeString(),
          securityMeta: {
            risk_score: 5,
            latency: data.latency ? Math.round(data.latency * 1000) : elapsed,
            tokens: data.usage?.total_tokens || 0,
            cache_hit: data.cache_hit || false,
          },
        };
        setMessages((prev) => [...prev, assistantMsg]);
      }
    } catch (err: any) {
      toast.error(`Request failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <AppShell title="Secure Chat Console">
      <div className="flex flex-col h-[calc(100vh-5.5rem)] dark-card overflow-hidden">
        {/* Chat Header Bar */}
        <div className="h-12 px-4 flex items-center justify-between border-b border-white/[0.06] bg-[#070a12]">
          <div className="flex items-center gap-2">
            <Bot className="w-4 h-4 text-zinc-400" />
            <span className="text-[13px] font-medium text-white">
              Secure AI Assistant
            </span>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="h-7 px-2 text-[11px] font-mono bg-[#12192a] text-zinc-200 border border-white/[0.06] rounded focus:outline-none"
            >
              <option value="groq/llama-3.3-70b-versatile">Groq - Llama 3.3 70B</option>
              <option value="groq/llama-3.1-8b-instant">Groq - Llama 3.1 8B</option>
              <option value="groq/mixtral-8x7b-32768">Groq - Mixtral 8x7B</option>
              <option value="ollama/llama3">Ollama - Llama 3 (Local)</option>
              <option value="ollama/mistral">Ollama - Mistral (Local)</option>
            </select>

            <button
              onClick={() =>
                setMessages([
                  {
                    id: "init_1",
                    role: "system",
                    content:
                      "LLM Security Gateway Pro connected. Zero-trust prompt interception, PII redaction, and output leakage monitoring active.",
                    timestamp: new Date().toLocaleTimeString(),
                  },
                ])
              }
              className="p-1 rounded text-zinc-400 hover:text-white transition-colors"
              title="Clear chat"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
          {messages.map((msg) => {
            const isUser = msg.role === "user";
            const isSystem = msg.role === "system";

            if (isSystem) {
              return (
                <div
                  key={msg.id}
                  className="flex justify-center select-none my-2"
                >
                  <div className="flex items-center gap-2 px-3 py-1 rounded bg-white/[0.03] border border-white/[0.06] text-zinc-400 text-[10.5px]">
                    <ShieldCheck className="w-3 h-3 text-zinc-400" />
                    <span>{msg.content}</span>
                  </div>
                </div>
              );
            }

            return (
              <div
                key={msg.id}
                className={`flex gap-2.5 max-w-2xl ${
                  isUser ? "ml-auto flex-row-reverse" : "mr-auto"
                }`}
              >
                {/* Avatar */}
                <div
                  className={`w-6 h-6 rounded flex items-center justify-center shrink-0 text-[11px] ${
                    isUser
                      ? "bg-white/[0.08] text-zinc-300"
                      : msg.securityMeta?.blocked
                      ? "bg-red-500/10 text-red-400"
                      : "bg-white/[0.05] text-zinc-400"
                  }`}
                >
                  {isUser ? <User className="w-3 h-3" /> : <Bot className="w-3 h-3" />}
                </div>

                {/* Message Bubble */}
                <div className="space-y-1 max-w-[85%]">
                  <div
                    className={`p-2.5 rounded text-[12px] leading-relaxed whitespace-pre-wrap ${
                      isUser
                        ? "bg-white/[0.08] text-white"
                        : msg.securityMeta?.blocked
                        ? "bg-red-950/20 text-red-200 border border-red-500/20 font-mono"
                        : "bg-[#12192a] text-zinc-200 border border-white/[0.04]"
                    }`}
                  >
                    {msg.content}
                  </div>

                  {/* Security Telemetry Badge */}
                  {msg.securityMeta && (
                    <div className="flex items-center gap-2 px-0.5 text-[9.5px] font-mono text-zinc-500">
                      {msg.securityMeta.blocked ? (
                        <span className="text-red-400">
                          BLOCKED (Risk: {msg.securityMeta.risk_score}/100)
                        </span>
                      ) : (
                        <>
                          <span className="text-zinc-400">Passed</span>
                          <span>•</span>
                          <span>{msg.securityMeta.latency}ms</span>
                          <span>•</span>
                          <span>{msg.securityMeta.tokens} tokens</span>
                          {msg.securityMeta.cache_hit && (
                            <>
                              <span>•</span>
                              <span className="text-zinc-300">CACHE HIT</span>
                            </>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {loading && (
            <div className="flex items-center gap-2 text-zinc-500 text-[10.5px] font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-ping" />
              <span>Evaluating prompt...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-2.5 border-t border-white/[0.06] bg-[#070a12]">
          <div className="relative flex items-center">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question or test guardrails (Enter to send)..."
              rows={1}
              className="w-full pl-3 pr-9 py-2 text-[12px] bg-[#0e1422] text-white placeholder-zinc-500 border border-white/[0.06] rounded focus:outline-none resize-none"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="absolute right-2 p-1 text-zinc-400 hover:text-white disabled:opacity-30 transition-colors"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
