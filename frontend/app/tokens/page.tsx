"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "@/components/layout/app-shell";
import {
  KeyRound,
  Plus,
  Copy,
  Trash2,
  Check,
} from "lucide-react";
import { toast } from "sonner";

interface ApiToken {
  id: number;
  token: string;
  name: string;
  provider: string;
  scope: string;
  created_at: string;
  last_used_at: string;
  active: boolean;
}

export default function TokensPage() {
  const [tokens, setTokens] = useState<ApiToken[]>([]);
  const [loading, setLoading] = useState(false);
  const [newTokenName, setNewTokenName] = useState("");
  const [newScope, setNewScope] = useState("read:write");
  const [newProvider, setNewProvider] = useState("All Models");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const fetchTokens = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/py/tokens");
      if (res.ok) {
        const data = await res.json();
        setTokens(data.tokens || []);
      }
    } catch {
      setTokens([
        {
          id: 1,
          token: "sg_live_948f98c8e19b489d82a17f",
          name: "Production Service Token",
          provider: "All Models",
          scope: "read:write",
          created_at: new Date().toISOString(),
          last_used_at: new Date().toISOString(),
          active: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTokens();
  }, []);

  const handleCreateToken = async () => {
    if (!newTokenName.trim()) {
      toast.error("Please enter a name for the token.");
      return;
    }

    try {
      const res = await fetch("/api/py/tokens", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newTokenName,
          provider: newProvider,
          scope: newScope,
        }),
      });

      if (res.ok) {
        toast.success("API Token generated.");
        setNewTokenName("");
        setShowCreateModal(false);
        fetchTokens();
      } else {
        toast.error("Failed to generate token.");
      }
    } catch {
      toast.error("Network error creating token.");
    }
  };

  const handleDeleteToken = async (id: number) => {
    try {
      const res = await fetch(`/api/py/tokens/${id}`, { method: "DELETE" });
      if (res.ok) {
        toast.info("Token revoked.");
        fetchTokens();
      }
    } catch {
      toast.error("Failed to revoke token.");
    }
  };

  const copyToClipboard = (token: string, id: number) => {
    navigator.clipboard.writeText(token);
    setCopiedId(id);
    toast.success("Copied to clipboard");
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <AppShell title="API Tokens & Service Keys">
      <div className="space-y-4">
        {/* Banner */}
        <div className="dark-card p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-white/[0.04] border border-white/[0.08] text-zinc-300">
              <KeyRound className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-[15px] font-medium text-white tracking-tight">
                API Tokens & Authentication Keys
              </h2>
              <p className="text-[11px] text-zinc-400">
                Generate scoped bearer tokens for downstream microservices and client applications.
              </p>
            </div>
          </div>

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[11.5px] font-medium text-black bg-white hover:bg-zinc-200 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Generate Token</span>
          </button>
        </div>

        {/* Tokens List */}
        <div className="dark-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[11.5px]">
              <thead className="bg-[#070a12] border-b border-white/[0.06] text-zinc-400 font-mono text-[10px]">
                <tr>
                  <th className="py-2.5 px-3">Token Name</th>
                  <th className="py-2.5 px-3">Key</th>
                  <th className="py-2.5 px-3">Provider</th>
                  <th className="py-2.5 px-3">Scope</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Created</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04] font-mono text-zinc-300">
                {tokens.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-zinc-500 font-sans">
                      No API tokens generated yet.
                    </td>
                  </tr>
                ) : (
                  tokens.map((t) => (
                    <tr key={t.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="py-2 px-3 font-sans font-medium text-white">{t.name}</td>
                      <td className="py-2 px-3">
                        <div className="flex items-center gap-1.5 text-zinc-300">
                          <span>{t.token.slice(0, 14)}••••••••</span>
                          <button
                            onClick={() => copyToClipboard(t.token, t.id)}
                            className="p-1 hover:text-white transition-colors"
                            title="Copy full token"
                          >
                            {copiedId === t.id ? (
                              <Check className="w-3 h-3 text-zinc-300" />
                            ) : (
                              <Copy className="w-3 h-3 text-zinc-500" />
                            )}
                          </button>
                        </div>
                      </td>
                      <td className="py-2 px-3 text-zinc-400">{t.provider}</td>
                      <td className="py-2 px-3">
                        <span className="px-1.5 py-0.2 rounded text-[9.5px] bg-white/[0.05] text-zinc-400 border border-white/[0.06]">
                          {t.scope}
                        </span>
                      </td>
                      <td className="py-2 px-3">
                        <span className="text-[9.5px] text-zinc-400">
                          ACTIVE
                        </span>
                      </td>
                      <td className="py-2 px-3 text-zinc-500 text-[10px]">
                        {new Date(t.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-2 px-3 text-right">
                        <button
                          onClick={() => handleDeleteToken(t.id)}
                          className="p-1 text-zinc-500 hover:text-red-400 transition-colors"
                          title="Revoke token"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Create Token Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="dark-card max-w-sm w-full p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
                <span className="text-[13px] font-medium text-white">
                  Generate Service Token
                </span>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-zinc-500 hover:text-white text-[12px]"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-2.5 text-[11.5px]">
                <div>
                  <label className="text-zinc-400 block mb-1">Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Production Analytics Worker"
                    value={newTokenName}
                    onChange={(e) => setNewTokenName(e.target.value)}
                    className="w-full h-7.5 px-2 bg-[#12192a] border border-white/[0.06] rounded text-white focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-zinc-400 block mb-1">Provider</label>
                  <select
                    value={newProvider}
                    onChange={(e) => setNewProvider(e.target.value)}
                    className="w-full h-7.5 px-2 bg-[#12192a] border border-white/[0.06] rounded text-white focus:outline-none"
                  >
                    <option value="All Models">All Models &amp; Providers</option>
                    <option value="Groq Models">Groq Models Only</option>
                    <option value="Ollama Local">Ollama Local Engine Only</option>
                  </select>
                </div>

                <div>
                  <label className="text-zinc-400 block mb-1">Scope</label>
                  <select
                    value={newScope}
                    onChange={(e) => setNewScope(e.target.value)}
                    className="w-full h-7.5 px-2 bg-[#12192a] border border-white/[0.06] rounded text-white focus:outline-none"
                  >
                    <option value="read:write">read:write (Full Completion Access)</option>
                    <option value="read">read (Telemetry Inspection Only)</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-white/[0.06]">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="px-2.5 py-1 text-[11px] text-zinc-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateToken}
                  className="px-3 py-1 text-[11px] font-medium bg-white text-black rounded hover:bg-zinc-200 transition-colors"
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
