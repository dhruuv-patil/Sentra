"use client";

import React, { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import {
  Layers,
  Plus,
} from "lucide-react";
import { toast } from "sonner";

interface ProjectEnv {
  id: string;
  name: string;
  description: string;
  environment: "Production" | "Staging" | "Development";
  activePolicies: number;
  totalRequests: number;
  blockedRate: string;
  lastActive: string;
}

const PROJECTS: ProjectEnv[] = [
  {
    id: "proj_prod_01",
    name: "Enterprise Core Production",
    description: "Primary client-facing LLM endpoints for customer support, workflow agents, and semantic search.",
    environment: "Production",
    activePolicies: 6,
    totalRequests: 4766,
    blockedRate: "99.0%",
    lastActive: "Just now",
  },
  {
    id: "proj_stg_02",
    name: "Internal Staging & QA",
    description: "Staging gateway for prompt engineering evaluation and red-teaming adversarial payloads.",
    environment: "Staging",
    activePolicies: 6,
    totalRequests: 842,
    blockedRate: "94.2%",
    lastActive: "14 mins ago",
  },
  {
    id: "proj_dev_03",
    name: "Developer Local Sandbox",
    description: "Isolated local development environment running against Ollama Llama 3 on developers' local machines.",
    environment: "Development",
    activePolicies: 4,
    totalRequests: 195,
    blockedRate: "62.5%",
    lastActive: "2 hours ago",
  },
];

export default function ProjectsPage() {
  const [projects] = useState<ProjectEnv[]>(PROJECTS);

  return (
    <AppShell title="Projects & Environments">
      <div className="space-y-4">
        {/* Banner */}
        <div className="dark-card p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded bg-white/[0.04] border border-white/[0.08] text-zinc-300">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-[15px] font-medium text-white tracking-tight">
                Gateway Projects &amp; Workspaces
              </h2>
              <p className="text-[11px] text-zinc-400">
                Segment guardrail policies, API tokens, and audit trails across isolated application environments.
              </p>
            </div>
          </div>

          <button
            onClick={() => toast.info("New environment wizard initiated.")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[11.5px] font-medium text-black bg-white hover:bg-zinc-200 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Environment</span>
          </button>
        </div>

        {/* Project Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
          {projects.map((p) => (
            <div
              key={p.id}
              className="dark-card p-4 flex flex-col justify-between space-y-3"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="px-1.5 py-0.2 rounded text-[9.5px] font-mono uppercase bg-white/[0.05] text-zinc-300 border border-white/[0.06]">
                    {p.environment}
                  </span>
                  <span className="text-[10px] font-mono text-zinc-500">{p.lastActive}</span>
                </div>

                <h3 className="text-[13.5px] font-medium text-white tracking-tight">
                  {p.name}
                </h3>
                <p className="text-[11px] text-zinc-400 leading-relaxed mt-1">
                  {p.description}
                </p>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-2 p-2 rounded bg-[#12192a] border border-white/[0.04] text-[10.5px] font-mono">
                <div>
                  <div className="text-zinc-500 text-[9px]">Requests</div>
                  <div className="text-white">{p.totalRequests.toLocaleString()}</div>
                </div>
                <div>
                  <div className="text-zinc-500 text-[9px]">Block Rate</div>
                  <div className="text-zinc-200">{p.blockedRate}</div>
                </div>
                <div>
                  <div className="text-zinc-500 text-[9px]">Policies</div>
                  <div className="text-zinc-300">{p.activePolicies} Active</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
