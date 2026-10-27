"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "@/components/layout/app-shell";
import {
  ShieldAlert,
  Save,
} from "lucide-react";
import { toast } from "sonner";

interface GuardrailPolicy {
  id: number;
  key: string;
  name: string;
  description: string;
  category: string;
  enabled: boolean;
  action: string;
  sensitivity: number;
  triggers_count: number;
  updated_at: string;
}

const DEFAULT_POLICIES: GuardrailPolicy[] = [
  {
    id: 1,
    key: "context_scanner_v3",
    name: "Context Scanner v3",
    description: "Deep semantic scanner analyzing multi-turn conversational intent, adversarial jailbreaks, and policy compliance.",
    category: "INPUT",
    enabled: true,
    action: "BLOCK",
    sensitivity: 0.80,
    triggers_count: 4645,
    updated_at: new Date().toISOString(),
  },
  {
    id: 2,
    key: "pii_masker",
    name: "SSN & PII Anonymizer",
    description: "Automatically detects and redacts SSNs, credit cards, emails, phone numbers, and bearer API tokens prior to LLM dispatch.",
    category: "INPUT",
    enabled: true,
    action: "REDACT",
    sensitivity: 0.90,
    triggers_count: 894,
    updated_at: new Date().toISOString(),
  },
  {
    id: 3,
    key: "prompt_injection",
    name: "Prompt Injection Shield",
    description: "Heuristic pattern matching against DAN exploits, delimiter override attacks, and recursive Base64 payload decoders.",
    category: "INPUT",
    enabled: true,
    action: "BLOCK",
    sensitivity: 0.85,
    triggers_count: 342,
    updated_at: new Date().toISOString(),
  },
  {
    id: 4,
    key: "output_harm_guard",
    name: "Harmful Output & System Leakage",
    description: "Boundary-enforced regex to prevent system prompt leakage, sensitive internal IP disclosure, and unsafe completions.",
    category: "OUTPUT",
    enabled: true,
    action: "BLOCK",
    sensitivity: 0.75,
    triggers_count: 48,
    updated_at: new Date().toISOString(),
  },
  {
    id: 5,
    key: "high_risk_hitl",
    name: "High-Risk HITL Gate",
    description: "Quarantines prompts exceeding risk threshold (Score > 50) and routes them to the administrator governance review queue.",
    category: "POLICY",
    enabled: true,
    action: "QUEUE",
    sensitivity: 0.50,
    triggers_count: 19,
    updated_at: new Date().toISOString(),
  },
  {
    id: 6,
    key: "regex_firewall",
    name: "Regex Behavioral Firewall",
    description: "Custom deterministic regex rules for proprietary token protection, corporate confidential patterns, and export rules.",
    category: "FILTER",
    enabled: true,
    action: "BLOCK",
    sensitivity: 0.95,
    triggers_count: 127,
    updated_at: new Date().toISOString(),
  },
];

export default function GuardrailsPage() {
  const [policies, setPolicies] = useState<GuardrailPolicy[]>(DEFAULT_POLICIES);
  const [loading, setLoading] = useState(false);
  const [savingKey, setSavingKey] = useState<string | null>(null);

  useEffect(() => {
    async function loadPolicies() {
      try {
        setLoading(true);
        const res = await fetch("/api/py/guardrails");
        if (res.ok) {
          const data = await res.json();
          if (data.guardrails && data.guardrails.length > 0) {
            setPolicies(data.guardrails);
          }
        }
      } catch (e) {
        console.warn("Using default guardrail policies", e);
      } finally {
        setLoading(false);
      }
    }
    loadPolicies();
  }, []);

  const handleToggle = (key: string) => {
    setPolicies((prev) =>
      prev.map((p) => (p.key === key ? { ...p, enabled: !p.enabled } : p))
    );
  };

  const handleActionChange = (key: string, action: string) => {
    setPolicies((prev) =>
      prev.map((p) => (p.key === key ? { ...p, action } : p))
    );
  };

  const handleSensitivityChange = (key: string, sensitivity: number) => {
    setPolicies((prev) =>
      prev.map((p) => (p.key === key ? { ...p, sensitivity } : p))
    );
  };

  const savePolicy = async (policy: GuardrailPolicy) => {
    try {
      setSavingKey(policy.key);
      const res = await fetch("/api/py/guardrails/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          key: policy.key,
          enabled: policy.enabled,
          action: policy.action,
          sensitivity: policy.sensitivity,
        }),
      });
      if (res.ok) {
        toast.success(`Guardrail "${policy.name}" updated.`);
      } else {
        toast.error("Failed to update policy.");
      }
    } catch {
      toast.info("Policy state saved locally.");
    } finally {
      setSavingKey(null);
    }
  };

  return (
    <AppShell title="Guardrails Policy Management">
      <div className="space-y-4">
        {/* Banner */}
        <div className="dark-card p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-white/[0.04] border border-white/[0.08] text-zinc-300">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-[15px] font-medium text-white tracking-tight">
                AI Guardrails Security Policies
              </h2>
              <p className="text-[11px] text-zinc-400">
                Enforce input filtering, PII anonymization, heuristic injection detection, and output guardrails in real time.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-zinc-400 bg-[#12192a] px-2.5 py-1 rounded border border-white/[0.06]">
              {policies.filter((p) => p.enabled).length} of {policies.length} Active
            </span>
          </div>
        </div>

        {/* Policy Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {policies.map((policy) => {
            const isSaving = savingKey === policy.key;

            return (
              <div
                key={policy.key}
                className={`dark-card p-4 flex flex-col justify-between transition-colors ${
                  policy.enabled ? "border-white/[0.1]" : "opacity-60"
                }`}
              >
                {/* Header */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-[13px] font-medium text-white">
                        {policy.name}
                      </span>
                      <span className="text-[9px] font-mono px-1.5 py-0.2 rounded uppercase bg-white/[0.05] text-zinc-400 border border-white/[0.08]">
                        {policy.category}
                      </span>
                    </div>

                    {/* Minimal Toggle Switch */}
                    <button
                      onClick={() => handleToggle(policy.key)}
                      className={`relative inline-flex h-4.5 w-8 shrink-0 cursor-pointer rounded-full border border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                        policy.enabled ? "bg-white/80" : "bg-white/10"
                      }`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-3.5 w-3.5 transform rounded-full bg-[#0e1422] shadow transition duration-200 ease-in-out ${
                          policy.enabled ? "translate-x-3.5" : "translate-x-0"
                        }`}
                      />
                    </button>
                  </div>

                  <p className="text-[11px] text-zinc-400 leading-relaxed mb-3">
                    {policy.description}
                  </p>
                </div>

                {/* Controls */}
                <div className="space-y-2.5 pt-2 border-t border-white/[0.06]">
                  <div className="grid grid-cols-2 gap-3">
                    {/* Action Selector */}
                    <div>
                      <label className="text-[10px] font-mono text-zinc-500 uppercase block mb-1">
                        Action
                      </label>
                      <select
                        value={policy.action}
                        disabled={!policy.enabled}
                        onChange={(e) => handleActionChange(policy.key, e.target.value)}
                        className="w-full h-7 px-2 text-[11px] font-mono bg-[#12192a] text-zinc-200 border border-white/[0.06] rounded focus:outline-none disabled:opacity-50"
                      >
                        <option value="BLOCK">BLOCK</option>
                        <option value="REDACT">REDACT</option>
                        <option value="QUEUE">QUEUE</option>
                        <option value="ALERT">ALERT</option>
                      </select>
                    </div>

                    {/* Sensitivity Slider */}
                    <div>
                      <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500 uppercase mb-1">
                        <span>Sensitivity</span>
                        <span className="text-zinc-300 font-medium">
                          {Math.round(policy.sensitivity * 100)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0.10"
                        max="1.00"
                        step="0.05"
                        value={policy.sensitivity}
                        disabled={!policy.enabled}
                        onChange={(e) =>
                          handleSensitivityChange(
                            policy.key,
                            parseFloat(e.target.value)
                          )
                        }
                        className="w-full h-1 bg-white/10 rounded appearance-none cursor-pointer accent-white disabled:opacity-50"
                      />
                    </div>
                  </div>

                  {/* Foot metadata & Save button */}
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[10px] font-mono text-zinc-500">
                      Triggers: <span className="text-zinc-300">{policy.triggers_count.toLocaleString()}</span>
                    </span>

                    <button
                      onClick={() => savePolicy(policy)}
                      disabled={isSaving}
                      className="px-2.5 py-1 text-[10.5px] font-medium text-zinc-200 hover:text-white bg-white/[0.05] hover:bg-white/[0.09] border border-white/[0.08] rounded transition-colors flex items-center gap-1"
                    >
                      <Save className={`w-3 h-3 ${isSaving ? "animate-spin" : ""}`} />
                      <span>{isSaving ? "Saving..." : "Apply"}</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </AppShell>
  );
}
