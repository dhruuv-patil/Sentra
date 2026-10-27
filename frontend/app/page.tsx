"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { MetricCard } from "@/components/dashboard/metric-card";
import { PromptsBlockedCard } from "@/components/dashboard/prompts-blocked-card";
import { GuardrailsCard } from "@/components/dashboard/guardrails-card";
import { BlockedUsersCard } from "@/components/dashboard/blocked-users-card";
import { ConnectionsChartCard } from "@/components/dashboard/connections-chart-card";
import { LatencyChartCard } from "@/components/dashboard/latency-chart-card";

// Restrained, minimal baseline data matching the uploaded reference screenshot
const DEFAULT_METRICS = {
  summary: {
    blocked_prompts: 4747,
    prompts_sent: 4766,
    blocked_rate: 99.0,
    blocked_responses: 38,
    most_used_model: "bjkim-claude",
    least_used_model: "chatgpt-hr",
    total_tokens: 1284500,
    total_cost: 4.281,
    pending_approvals: 0,
  },
  prompts_and_blocked: [
    { label: "10/06", prompts_sent: 120, blocked_prompts: 115, blocked_responses: 2 },
    { label: "11/01", prompts_sent: 240, blocked_prompts: 232, blocked_responses: 4 },
    { label: "12/01", prompts_sent: 480, blocked_prompts: 470, blocked_responses: 6 },
    { label: "01/01", prompts_sent: 760, blocked_prompts: 745, blocked_responses: 9 },
    { label: "02/15", prompts_sent: 2980, blocked_prompts: 2940, blocked_responses: 28 },
    { label: "03/20", prompts_sent: 1820, blocked_prompts: 1810, blocked_responses: 16 },
    { label: "04/07", prompts_sent: 420, blocked_prompts: 412, blocked_responses: 5 },
  ],
  policy_guardrails: {
    most_active: "Context Scanner v3",
    most_active_label: "Most active guardrail",
    least_active: "SSN scanner",
    least_active_label: "Least active guardrail",
    description: "Context Scanner v3 accounts for more than 6% of total blocked prompts.",
  },
  most_blocked_users: [
    { rank: 1, user_id: "2040", blocked: 4645, trend: "up" as const, change: "+12%" },
    { rank: 2, user_id: "2040(Edward)", blocked: 64, trend: "up" as const, change: "+4%" },
    { rank: 3, user_id: "2040 (John)", blocked: 7, trend: "up" as const, change: "+1%" },
    { rank: 4, user_id: "2040 (Kenneth)", blocked: 6, trend: "down" as const, change: "-2%" },
    { rank: 5, user_id: "only-for-claude", blocked: 6, trend: "up" as const, change: "+1%" },
  ],
  connections_usage: [
    { name: "chatgpt-global (openai)", provider: "openai", prompts: 7.2, raw_count: 2840, color: "#d96565" },
    { name: "bjkim-claude (anthropic)", provider: "anthropic", prompts: 4.1, raw_count: 1620, color: "#439e73" },
    { name: "chatgpt-tech (openai)", provider: "openai", prompts: 1.8, raw_count: 710, color: "#4d78a8" },
  ],
  latency_per_provider: [
    { date: "01 Nov", anthropic: 1800, openai: 2400, groq: 280 },
    { date: "15 Nov", anthropic: 12500, openai: 3100, groq: 310 },
    { date: "01 Dec", anthropic: 1900, openai: 2200, groq: 250 },
    { date: "15 Dec", anthropic: 7600, openai: 2900, groq: 290 },
    { date: "01 Jan", anthropic: 2100, openai: 11800, groq: 340 },
    { date: "15 Jan", anthropic: 6900, openai: 2300, groq: 270 },
    { date: "01 Feb", anthropic: 2400, openai: 7800, groq: 320 },
    { date: "15 Feb", anthropic: 8300, openai: 2500, groq: 280 },
    { date: "01 Mar", anthropic: 2200, openai: 9400, groq: 310 },
    { date: "15 Mar", anthropic: 8900, openai: 2100, groq: 260 },
    { date: "01 Apr", anthropic: 1950, openai: 2400, groq: 275 },
  ],
};

export default function DashboardPage() {
  const [data, setData] = useState(DEFAULT_METRICS);
  const [range, setRange] = useState("10월 06일/25년 - 4월 07일/26년");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function fetchStats() {
      try {
        setLoading(true);
        const res = await fetch(`/api/py/dashboard/stats?filter=${encodeURIComponent(range)}`);
        if (res.ok) {
          const stats = await res.json();
          setData(stats);
        }
      } catch (e) {
        console.warn("Using baseline dashboard metrics", e);
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, [range]);

  return (
    <AppShell
      title="Dashboard"
      selectedRange={range}
      onRangeChange={(newRange) => setRange(newRange)}
    >
      <div className="space-y-3.5">
        {/* ROW 1: Key Metrics & Grouped Bar Chart */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5 items-stretch">
          {/* Left Column: 4 Stat Cards in 2x2 Grid */}
          <div className="lg:col-span-5 grid grid-cols-2 gap-3.5 h-full">
            <MetricCard
              title="Blocked prompts"
              value={data.summary.blocked_prompts.toLocaleString()}
              showSparkline={true}
              className="h-full"
            />
            <MetricCard
              title="Prompts sent"
              value={data.summary.prompts_sent.toLocaleString()}
              showSparkline={true}
              className="h-full"
            />
            <MetricCard
              title="Most used model"
              value={data.summary.most_used_model}
              isModelCard={true}
              className="h-full"
            />
            <MetricCard
              title="Least used model"
              value={data.summary.least_used_model}
              isModelCard={true}
              className="h-full"
            />
          </div>

          {/* Right Column: Prompts sent and blocked */}
          <div className="lg:col-span-7 h-full">
            <PromptsBlockedCard
              percentage={data.summary.blocked_rate}
              data={data.prompts_and_blocked}
              className="h-full"
            />
          </div>
        </div>

        {/* ROW 2: Policy Management Guardrails & Most Blocked Users */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5 items-stretch">
          {/* Left: Policy Management Guardrails */}
          <div className="lg:col-span-7 h-full">
            <GuardrailsCard
              mostActive={data.policy_guardrails.most_active}
              mostActiveLabel={data.policy_guardrails.most_active_label}
              leastActive={data.policy_guardrails.least_active}
              leastActiveLabel={data.policy_guardrails.least_active_label}
              description={data.policy_guardrails.description}
              className="h-full"
            />
          </div>

          {/* Right: Most Blocked Prompts per User */}
          <div className="lg:col-span-5 h-full">
            <BlockedUsersCard
              users={data.most_blocked_users}
              className="h-full"
            />
          </div>
        </div>

        {/* ROW 3: Top 5 Connections & Latency per Provider */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5 items-stretch">
          {/* Left: Top 5 connections by usage */}
          <div className="lg:col-span-6 h-full">
            <ConnectionsChartCard
              data={data.connections_usage}
              className="h-full"
            />
          </div>

          {/* Right: Latency per LLM provider */}
          <div className="lg:col-span-6 h-full">
            <LatencyChartCard
              data={data.latency_per_provider}
              className="h-full"
            />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
