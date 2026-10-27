"use client";

import React, { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import {
  BookOpen,
  Copy,
  Check,
} from "lucide-react";
import { toast } from "sonner";

export default function DocsPage() {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const copyCode = (code: string, id: string) => {
    navigator.clipboard.writeText(code);
    setCopiedKey(id);
    toast.success("Snippet copied");
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const curlSnippet = `curl -X POST http://localhost:8000/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_TOKEN" \\
  -d '{
    "model": "groq/llama-3.3-70b-versatile",
    "messages": [
      {"role": "user", "content": "Explain zero-trust architecture."}
    ],
    "user": "developer_2040"
  }'`;

  const pythonSnippet = `import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="sg_live_production_key"
)

response = client.chat.completions.create(
    model="groq/llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Analyze system requirements."}],
    extra_body={"user": "dhruv_patil"}
)

print(response.choices[0].message.content)`;

  const wsSnippet = `const ws = new WebSocket("ws://localhost:8000/ws/logs");

ws.onmessage = (event) => {
  const telemetry = JSON.parse(event.data);
  console.log("Gateway Event:", telemetry);
};`;

  return (
    <AppShell title="API Documentation & SDK Reference">
      <div className="space-y-4">
        {/* Banner */}
        <div className="dark-card p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-white/[0.04] border border-white/[0.08] text-zinc-300">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-[15px] font-medium text-white tracking-tight">
                LLM Security Gateway Pro API Reference
              </h2>
              <p className="text-[11px] text-zinc-400">
                100% OpenAI-compatible API format with automatic security interception, PII scrubbing, and cached completions.
              </p>
            </div>
          </div>
        </div>

        {/* Code Blocks */}
        <div className="space-y-3.5">
          {/* Section 1: cURL */}
          <div className="dark-card p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[12.5px] font-medium text-white">
                1. Standard Chat Completions (cURL)
              </span>
              <button
                onClick={() => copyCode(curlSnippet, "curl")}
                className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[10.5px] text-zinc-400 hover:text-white bg-[#12192a] border border-white/[0.06]"
              >
                {copiedKey === "curl" ? <Check className="w-3 h-3 text-zinc-300" /> : <Copy className="w-3 h-3" />}
                <span>Copy</span>
              </button>
            </div>
            <pre className="p-3 rounded bg-[#12192a] border border-white/[0.04] text-[11px] font-mono text-zinc-300 overflow-x-auto leading-relaxed">
              {curlSnippet}
            </pre>
          </div>

          {/* Section 2: Python SDK */}
          <div className="dark-card p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[12.5px] font-medium text-white">
                2. Python OpenAI Client Drop-in Replacement
              </span>
              <button
                onClick={() => copyCode(pythonSnippet, "python")}
                className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[10.5px] text-zinc-400 hover:text-white bg-[#12192a] border border-white/[0.06]"
              >
                {copiedKey === "python" ? <Check className="w-3 h-3 text-zinc-300" /> : <Copy className="w-3 h-3" />}
                <span>Copy</span>
              </button>
            </div>
            <pre className="p-3 rounded bg-[#12192a] border border-white/[0.04] text-[11px] font-mono text-zinc-300 overflow-x-auto leading-relaxed">
              {pythonSnippet}
            </pre>
          </div>

          {/* Section 3: WebSocket */}
          <div className="dark-card p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[12.5px] font-medium text-white">
                3. Real-Time Telemetry Stream (WebSocket)
              </span>
              <button
                onClick={() => copyCode(wsSnippet, "ws")}
                className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[10.5px] text-zinc-400 hover:text-white bg-[#12192a] border border-white/[0.06]"
              >
                {copiedKey === "ws" ? <Check className="w-3 h-3 text-zinc-300" /> : <Copy className="w-3 h-3" />}
                <span>Copy</span>
              </button>
            </div>
            <pre className="p-3 rounded bg-[#12192a] border border-white/[0.04] text-[11px] font-mono text-zinc-300 overflow-x-auto leading-relaxed">
              {wsSnippet}
            </pre>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
