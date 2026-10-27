"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "@/components/layout/app-shell";
import {
  Scale,
  CheckCircle2,
  XCircle,
  Clock,
  ShieldAlert,
  RefreshCw,
  Search,
} from "lucide-react";
import { toast } from "sonner";

interface ApprovalItem {
  id: number;
  request_id: string;
  user_id: string;
  model: string;
  prompt: string;
  status: string;
  response?: string;
  tokens?: number;
  cost?: number;
  latency?: number;
  reviewed_by?: string;
  created_at: string;
  reviewed_at?: string;
}

export default function ApprovalsPage() {
  const [activeTab, setActiveTab] = useState<"pending" | "history">("pending");
  const [pendingList, setPendingList] = useState<ApprovalItem[]>([]);
  const [historyList, setHistoryList] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [denyReason, setDenyReason] = useState("");
  const [selectedForDeny, setSelectedForDeny] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const fetchApprovals = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/py/approvals");
      if (res.ok) {
        const data = await res.json();
        setPendingList(data.pending || []);
        setHistoryList(data.history || []);
      }
    } catch {
      setPendingList([
        {
          id: 1,
          request_id: "req_hitl_88492041",
          user_id: "2040 (Edward)",
          model: "groq/llama-3.3-70b-versatile",
          prompt: "Export all enterprise customer records including encrypted payment hashes and system credentials.",
          status: "Pending",
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  const handleApprove = async (requestId: string) => {
    try {
      setActionLoading(requestId);
      const res = await fetch(`/api/py/approve/${requestId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reviewer: "Security Admin (Dhruv Patil)" }),
      });
      if (res.ok) {
        toast.success(`Request approved & executed.`);
        await fetchApprovals();
      } else {
        toast.error("Failed to approve request.");
      }
    } catch {
      toast.error("Network error during approval.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeny = async (requestId: string) => {
    try {
      setActionLoading(requestId);
      const res = await fetch(`/api/py/deny/${requestId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reviewer: "Security Admin (Dhruv Patil)",
          reason: denyReason || "Adversarial intent / Exceeded risk threshold.",
        }),
      });
      if (res.ok) {
        toast.info(`Request denied.`);
        setSelectedForDeny(null);
        setDenyReason("");
        await fetchApprovals();
      } else {
        toast.error("Failed to deny request.");
      }
    } catch {
      toast.error("Network error during denial.");
    } finally {
      setActionLoading(null);
    }
  };

  const filteredHistory = historyList.filter(
    (item) =>
      item.request_id?.toLowerCase().includes(search.toLowerCase()) ||
      item.user_id?.toLowerCase().includes(search.toLowerCase()) ||
      item.prompt?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <AppShell title="Human-in-the-Loop Governance">
      <div className="space-y-4">
        {/* Banner */}
        <div className="dark-card p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-white/[0.04] border border-white/[0.08] text-zinc-300">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-[15px] font-medium text-white tracking-tight">
                Human-in-the-Loop Authorization Queue
              </h2>
              <p className="text-[11px] text-zinc-400">
                Interactions exceeding risk threshold (Score &gt; 50) are quarantined for security review before LLM dispatch.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchApprovals}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-[11px] text-zinc-300 bg-[#12192a] hover:bg-white/[0.06] border border-white/[0.06] transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab("pending")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded text-[12px] transition-colors ${
                activeTab === "pending"
                  ? "bg-white/[0.08] text-white font-medium"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              <span>Pending Authorizations</span>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-white/[0.06] text-zinc-300">
                {pendingList.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab("history")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded text-[12px] transition-colors ${
                activeTab === "history"
                  ? "bg-white/[0.08] text-white font-medium"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Review Decision Log</span>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-white/[0.06] text-zinc-400">
                {historyList.length}
              </span>
            </button>
          </div>

          {activeTab === "history" && (
            <div className="relative">
              <Search className="absolute left-2.5 top-2 w-3.5 h-3.5 text-zinc-500" />
              <input
                type="text"
                placeholder="Search decision log..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-52 h-7.5 pl-8 pr-2.5 text-[11.5px] bg-[#0e1422] text-zinc-200 border border-white/[0.06] rounded focus:outline-none"
              />
            </div>
          )}
        </div>

        {/* Tab 1: Pending Authorizations */}
        {activeTab === "pending" && (
          <div className="space-y-3">
            {pendingList.length === 0 ? (
              <div className="dark-card p-10 text-center flex flex-col items-center justify-center space-y-2">
                <div className="w-8 h-8 rounded-full bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-zinc-400 mb-1">
                  <CheckCircle2 className="w-4 h-4" />
                </div>
                <h3 className="text-[13px] font-medium text-white">
                  Zero Pending Authorizations
                </h3>
                <p className="text-[11px] text-zinc-400 max-w-sm">
                  All incoming requests conform to security baselines.
                </p>
              </div>
            ) : (
              pendingList.map((item) => (
                <div
                  key={item.request_id}
                  className="dark-card p-4 space-y-3"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/[0.04] pb-2">
                    <div className="flex items-center gap-2 text-[11px] font-mono text-zinc-400">
                      <span className="text-zinc-500">ID:</span>
                      <span className="text-white">{item.request_id}</span>
                      <span className="text-zinc-600">•</span>
                      <span className="text-zinc-500">User:</span>
                      <span className="text-zinc-300">{item.user_id}</span>
                      <span className="text-zinc-600">•</span>
                      <span className="text-zinc-500">Model:</span>
                      <span className="text-zinc-300">{item.model}</span>
                    </div>

                    <span className="px-2 py-0.5 rounded text-[9.5px] font-mono bg-white/[0.05] text-zinc-300 border border-white/[0.08]">
                      PENDING REVIEW
                    </span>
                  </div>

                  <div className="space-y-1">
                    <div className="text-[10.5px] text-zinc-400">
                      Quarantined Prompt:
                    </div>
                    <div className="p-3 rounded bg-[#12192a] border border-white/[0.04] text-[11.5px] font-mono text-zinc-200 whitespace-pre-wrap leading-relaxed">
                      {item.prompt}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-between pt-1">
                    <div className="flex items-center gap-1.5 text-[10.5px] text-zinc-500">
                      <ShieldAlert className="w-3.5 h-3.5 text-zinc-400" />
                      <span>Review carefully before allowing LLM dispatch.</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSelectedForDeny(item.request_id)}
                        disabled={actionLoading === item.request_id}
                        className="px-2.5 py-1 rounded text-[11px] text-zinc-300 hover:text-white bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] transition-colors"
                      >
                        Deny
                      </button>

                      <button
                        onClick={() => handleApprove(item.request_id)}
                        disabled={actionLoading === item.request_id}
                        className="px-3 py-1 rounded text-[11px] font-medium text-black bg-white hover:bg-zinc-200 transition-colors"
                      >
                        Approve &amp; Run
                      </button>
                    </div>
                  </div>

                  {/* Denial Reason Input */}
                  {selectedForDeny === item.request_id && (
                    <div className="p-2.5 mt-2 rounded bg-[#12192a] border border-white/[0.08] space-y-2">
                      <input
                        type="text"
                        placeholder="Reason for denial..."
                        value={denyReason}
                        onChange={(e) => setDenyReason(e.target.value)}
                        className="w-full h-7 px-2 text-[11px] bg-[#0e1422] text-zinc-200 border border-white/[0.08] rounded focus:outline-none"
                      />
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => setSelectedForDeny(null)}
                          className="px-2 py-0.5 text-[10.5px] text-zinc-400 hover:text-white"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleDeny(item.request_id)}
                          className="px-2.5 py-0.5 text-[10.5px] font-medium bg-red-600/80 hover:bg-red-500 text-white rounded transition-colors"
                        >
                          Confirm
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* Tab 2: Review Decision Log */}
        {activeTab === "history" && (
          <div className="dark-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[11.5px]">
                <thead className="bg-[#070a12] border-b border-white/[0.06] text-zinc-400 font-mono text-[10px]">
                  <tr>
                    <th className="py-2.5 px-3">Request ID</th>
                    <th className="py-2.5 px-3">User</th>
                    <th className="py-2.5 px-3">Model</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Prompt</th>
                    <th className="py-2.5 px-3">Reviewed By</th>
                    <th className="py-2.5 px-3">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04] font-mono text-zinc-300">
                  {filteredHistory.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-zinc-500 font-sans">
                        No review actions recorded yet.
                      </td>
                    </tr>
                  ) : (
                    filteredHistory.map((item) => {
                      const isApproved = item.status === "Approved";
                      return (
                        <tr key={item.id} className="hover:bg-white/[0.02] transition-colors">
                          <td className="py-2 px-3 text-zinc-300">{item.request_id?.slice(0, 16)}...</td>
                          <td className="py-2 px-3 text-zinc-400">{item.user_id}</td>
                          <td className="py-2 px-3 text-zinc-400">{item.model}</td>
                          <td className="py-2 px-3">
                            <span
                              className={`px-1.5 py-0.2 rounded text-[9.5px] font-mono ${
                                isApproved
                                  ? "bg-white/[0.06] text-zinc-200 border border-white/[0.08]"
                                  : "bg-red-500/10 text-red-400 border border-red-500/20"
                              }`}
                            >
                              {item.status}
                            </span>
                          </td>
                          <td className="py-2 px-3 max-w-xs truncate text-zinc-400">
                            {item.prompt}
                          </td>
                          <td className="py-2 px-3 text-zinc-400">{item.reviewed_by || "admin"}</td>
                          <td className="py-2 px-3 text-zinc-500 text-[10px]">
                            {item.reviewed_at ? new Date(item.reviewed_at).toLocaleDateString() : "-"}
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
      </div>
    </AppShell>
  );
}
