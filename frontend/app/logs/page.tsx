"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "@/components/layout/app-shell";
import {
  FileCode2,
  Search,
  Download,
  RefreshCw,
  Activity,
  Lock,
} from "lucide-react";
import { toast } from "sonner";

interface AuditLog {
  id: number;
  request_id: string;
  user_id: string;
  model: string;
  prompt: string;
  response: string;
  tokens: number;
  cost: number;
  risk_score: number;
  latency: number;
  created_at: string;
}

interface HarmfulLog {
  id: number;
  request_id: string;
  user_id: string;
  prompt: string;
  category: string;
  risk_score: number;
  created_at: string;
}

export default function LogsPage() {
  const [activeTab, setActiveTab] = useState<"audit" | "harmful" | "live">("audit");
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [harmfulLogs, setHarmfulLogs] = useState<HarmfulLog[]>([]);
  const [liveEvents, setLiveEvents] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const auditRes = await fetch(
        `/api/py/logs?search=${encodeURIComponent(search)}&risk=${riskFilter}`
      );
      if (auditRes.ok) {
        const data = await auditRes.json();
        setAuditLogs(data.logs || []);
      }

      const harmfulRes = await fetch("/api/py/security/harmful");
      if (harmfulRes.ok) {
        const hData = await harmfulRes.json();
        setHarmfulLogs(hData || []);
      }
    } catch {
      setAuditLogs([
        {
          id: 1,
          request_id: "req_f8120a81-9921",
          user_id: "2040",
          model: "groq/llama-3.3-70b-versatile",
          prompt: "Verify the zero-trust policy settings for cloud deployment.",
          response: "Zero-trust architecture requires verifying explicitly, using least privileged access, and assuming breach.",
          tokens: 284,
          cost: 0.0005,
          risk_score: 5,
          latency: 0.38,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [riskFilter]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    if (activeTab === "live") {
      const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${wsProtocol}//${window.location.host}/ws/logs`;
      try {
        ws = new WebSocket(wsUrl);
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setLiveEvents((prev) => [
              { ...data, timestamp: new Date().toLocaleTimeString() },
              ...prev.slice(0, 49),
            ]);
          } catch {}
        };
      } catch {}
    }
    return () => {
      if (ws) ws.close();
    };
  }, [activeTab]);

  const handleExportCSV = () => {
    const csvContent =
      "data:text/csv;charset=utf-8," +
      ["ID,Request ID,User,Model,Tokens,Cost,Risk Score,Latency,Timestamp"]
        .concat(
          auditLogs.map(
            (l) =>
              `${l.id},"${l.request_id}","${l.user_id}","${l.model}",${l.tokens},${l.cost},${l.risk_score},${l.latency},"${l.created_at}"`
          )
        )
        .join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `llm_gateway_audit_logs_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success("Audit logs exported to CSV");
  };

  return (
    <AppShell title="Audit Logs & Telemetry">
      <div className="space-y-4">
        {/* Header Controls */}
        <div className="dark-card p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-white/[0.04] border border-white/[0.08] text-zinc-300">
              <FileCode2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-[15px] font-medium text-white tracking-tight">
                Decrypted Audit Trail & Threat Telemetry
              </h2>
              <p className="text-[11px] text-zinc-400">
                AES-256 Fernet encrypted logs at rest, transparently decrypted in memory for authorized administrators.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleExportCSV}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-[11px] text-zinc-300 bg-[#12192a] hover:bg-white/[0.06] border border-white/[0.06] transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export CSV</span>
            </button>

            <button
              onClick={fetchLogs}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-[11px] text-zinc-300 bg-[#12192a] hover:bg-white/[0.06] border border-white/[0.06] transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Tab Switcher & Filter Toolbar */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-2">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab("audit")}
              className={`px-3 py-1.5 rounded text-[12px] transition-colors ${
                activeTab === "audit"
                  ? "bg-white/[0.08] text-white font-medium"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              Audit Logs ({auditLogs.length})
            </button>
            <button
              onClick={() => setActiveTab("harmful")}
              className={`px-3 py-1.5 rounded text-[12px] transition-colors ${
                activeTab === "harmful"
                  ? "bg-white/[0.08] text-white font-medium"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              Harmful Blocks ({harmfulLogs.length})
            </button>
            <button
              onClick={() => setActiveTab("live")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[12px] transition-colors ${
                activeTab === "live"
                  ? "bg-white/[0.08] text-white font-medium"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              <Activity className="w-3.5 h-3.5 text-zinc-400" />
              <span>Live WebSocket Feed</span>
            </button>
          </div>

          {activeTab === "audit" && (
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <select
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value)}
                className="h-7 px-2 text-[11px] font-mono bg-[#12192a] text-zinc-300 border border-white/[0.06] rounded"
              >
                <option value="all">All Risk Scores</option>
                <option value="high">High Risk (&gt; 50)</option>
                <option value="low">Safe Risk (&lt;= 50)</option>
              </select>

              <div className="relative flex-1 sm:w-44">
                <Search className="absolute left-2.5 top-2 w-3.5 h-3.5 text-zinc-500" />
                <input
                  type="text"
                  placeholder="Search logs..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && fetchLogs()}
                  className="w-full h-7 pl-8 pr-2 text-[11px] bg-[#12192a] text-zinc-200 border border-white/[0.06] rounded focus:outline-none"
                />
              </div>
            </div>
          )}
        </div>

        {/* Tab 1: Audit Logs Table */}
        {activeTab === "audit" && (
          <div className="dark-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[11.5px]">
                <thead className="bg-[#070a12] border-b border-white/[0.06] text-zinc-400 font-mono text-[10px]">
                  <tr>
                    <th className="py-2.5 px-3">Request ID</th>
                    <th className="py-2.5 px-3">User</th>
                    <th className="py-2.5 px-3">Model</th>
                    <th className="py-2.5 px-3">Risk</th>
                    <th className="py-2.5 px-3">Tokens</th>
                    <th className="py-2.5 px-3">Latency</th>
                    <th className="py-2.5 px-3">Prompt</th>
                    <th className="py-2.5 px-3">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04] font-mono text-zinc-300">
                  {auditLogs.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-zinc-500 font-sans">
                        No audit records match query.
                      </td>
                    </tr>
                  ) : (
                    auditLogs.map((log) => {
                      const isHighRisk = log.risk_score > 50;
                      return (
                        <tr
                          key={log.id}
                          onClick={() => setSelectedLog(log)}
                          className="hover:bg-white/[0.02] cursor-pointer transition-colors"
                        >
                          <td className="py-2 px-3 text-zinc-200 font-medium">
                            {log.request_id?.slice(0, 16)}...
                          </td>
                          <td className="py-2 px-3 text-zinc-400">{log.user_id}</td>
                          <td className="py-2 px-3 text-zinc-400">{log.model}</td>
                          <td className="py-2 px-3">
                            <span
                              className={`px-1.5 py-0.2 rounded text-[9.5px] ${
                                isHighRisk
                                  ? "bg-red-500/10 text-red-400 border border-red-500/20"
                                  : "text-zinc-400"
                              }`}
                            >
                              {log.risk_score}/100
                            </span>
                          </td>
                          <td className="py-2 px-3 text-zinc-400">{log.tokens}</td>
                          <td className="py-2 px-3 text-zinc-400">
                            {typeof log.latency === "number" ? `${log.latency}s` : "-"}
                          </td>
                          <td className="py-2 px-3 max-w-xs truncate text-zinc-400 font-sans">
                            {log.prompt}
                          </td>
                          <td className="py-2 px-3 text-zinc-500 text-[10px]">
                            {new Date(log.created_at).toLocaleTimeString()}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 2: Harmful Violations Table */}
        {activeTab === "harmful" && (
          <div className="dark-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[11.5px]">
                <thead className="bg-[#070a12] border-b border-white/[0.06] text-zinc-400 font-mono text-[10px]">
                  <tr>
                    <th className="py-2.5 px-3">Request ID</th>
                    <th className="py-2.5 px-3">User</th>
                    <th className="py-2.5 px-3">Category</th>
                    <th className="py-2.5 px-3">Risk</th>
                    <th className="py-2.5 px-3">Prompt</th>
                    <th className="py-2.5 px-3">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04] font-mono text-zinc-300">
                  {harmfulLogs.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-zinc-500 font-sans">
                        Zero policy violations logged.
                      </td>
                    </tr>
                  ) : (
                    harmfulLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-red-950/10 transition-colors">
                        <td className="py-2 px-3 text-zinc-300">{log.request_id?.slice(0, 16)}...</td>
                        <td className="py-2 px-3 text-zinc-400">{log.user_id}</td>
                        <td className="py-2 px-3">
                          <span className="px-1.5 py-0.2 rounded text-[9.5px] bg-red-500/10 text-red-400 border border-red-500/20">
                            {log.category}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-red-400">{log.risk_score}</td>
                        <td className="py-2 px-3 max-w-sm truncate text-zinc-400 font-sans">
                          {log.prompt}
                        </td>
                        <td className="py-2 px-3 text-zinc-500 text-[10px]">
                          {new Date(log.created_at).toLocaleTimeString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 3: Live WebSocket Terminal Feed */}
        {activeTab === "live" && (
          <div className="dark-card p-4 space-y-2 bg-[#070a12] font-mono">
            <div className="flex items-center justify-between text-[11px] text-zinc-400 border-b border-white/[0.06] pb-2">
              <span className="flex items-center gap-2">
                <span>Connected to /ws/logs</span>
              </span>
              <button
                onClick={() => setLiveEvents([])}
                className="text-zinc-500 hover:text-white"
              >
                Clear
              </button>
            </div>

            <div className="space-y-1 max-h-80 overflow-y-auto text-[11px]">
              {liveEvents.length === 0 ? (
                <div className="text-zinc-600 py-6 text-center font-sans">
                  Awaiting gateway events...
                </div>
              ) : (
                liveEvents.map((ev, i) => (
                  <div
                    key={i}
                    className="p-1.5 rounded bg-[#12192a] border border-white/[0.04] flex items-center justify-between text-zinc-300"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-zinc-400">[{ev.type}]</span>
                      <span className="truncate">{ev.message || JSON.stringify(ev)}</span>
                    </div>
                    <span className="text-zinc-600 text-[10px] shrink-0 ml-2">
                      {ev.timestamp}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Modal: Decrypted Log Details */}
        {selectedLog && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="dark-card max-w-xl w-full p-4 space-y-3 max-h-[85vh] overflow-y-auto">
              <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
                <div className="flex items-center gap-2">
                  <Lock className="w-3.5 h-3.5 text-zinc-400" />
                  <span className="text-[12.5px] font-medium text-white">
                    Decrypted Audit Record
                  </span>
                </div>
                <button
                  onClick={() => setSelectedLog(null)}
                  className="text-zinc-400 hover:text-white text-[12px]"
                >
                  ✕
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[10.5px] font-mono">
                <div>
                  <span className="text-zinc-500">Request:</span>{" "}
                  <span className="text-zinc-200">{selectedLog.request_id}</span>
                </div>
                <div>
                  <span className="text-zinc-500">Model:</span>{" "}
                  <span className="text-zinc-200">{selectedLog.model}</span>
                </div>
                <div>
                  <span className="text-zinc-500">Tokens:</span>{" "}
                  <span className="text-zinc-200">{selectedLog.tokens}</span>
                </div>
                <div>
                  <span className="text-zinc-500">Risk Score:</span>{" "}
                  <span className="text-zinc-200">{selectedLog.risk_score}/100</span>
                </div>
              </div>

              <div>
                <div className="text-[10.5px] text-zinc-400 mb-1">
                  Prompt:
                </div>
                <div className="p-2.5 rounded bg-[#12192a] border border-white/[0.04] text-[11px] font-mono text-zinc-200 whitespace-pre-wrap">
                  {selectedLog.prompt}
                </div>
              </div>

              <div>
                <div className="text-[10.5px] text-zinc-400 mb-1">
                  Response:
                </div>
                <div className="p-2.5 rounded bg-[#12192a] border border-white/[0.04] text-[11px] font-mono text-zinc-200 whitespace-pre-wrap max-h-48 overflow-y-auto">
                  {selectedLog.response}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
