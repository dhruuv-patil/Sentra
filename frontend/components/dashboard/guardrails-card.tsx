"use client";

import React, { useState } from "react";
import { SlidersHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";

interface GuardrailsCardProps {
  mostActive?: string;
  mostActiveLabel?: string;
  leastActive?: string;
  leastActiveLabel?: string;
  description?: string;
  className?: string;
}

export function GuardrailsCard({
  mostActive = "Context Scanner v3",
  mostActiveLabel = "Most active guardrail",
  leastActive = "SSN scanner",
  leastActiveLabel = "Least active guardrail",
  description = "Context Scanner v3 accounts for more than 6% of total blocked prompts.",
  className,
}: GuardrailsCardProps) {
  const [showPolicies, setShowPolicies] = useState(false);

  return (
    <div className={cn("dark-card p-4 flex flex-col justify-between select-none", className)}>
      {/* Title */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] font-normal text-zinc-400">
          Policy management guardrails
        </span>
        <button
          onClick={() => setShowPolicies(!showPolicies)}
          className="text-[10px] text-zinc-500 hover:text-zinc-300 flex items-center gap-1 transition-colors font-mono"
        >
          <SlidersHorizontal className="w-3 h-3" />
          <span>{showPolicies ? "Default View" : "Rules"}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center flex-1">
        {/* Left Column matching screenshot */}
        <div className="md:col-span-6 flex flex-col justify-between space-y-3 pr-2">
          <div>
            <div className="text-[13.5px] font-medium text-white">
              {mostActive}
            </div>
            <div className="text-[10.5px] text-zinc-400">
              {mostActiveLabel}
            </div>
          </div>

          <div>
            <div className="text-[13.5px] font-medium text-white">
              {leastActive}
            </div>
            <div className="text-[10.5px] text-zinc-400">
              {leastActiveLabel}
            </div>
          </div>

          <div className="text-[10px] text-zinc-500 leading-normal pt-1">
            {description}
          </div>
        </div>

        {/* Right Column matching screenshot */}
        <div className="md:col-span-6 flex flex-col items-center justify-center border-l border-white/[0.06] pl-4 py-2 min-h-[110px]">
          {showPolicies ? (
            <div className="w-full space-y-1.5 text-[10px] font-mono">
              <div className="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span className="text-zinc-300">Prompt Injection Shield</span>
                <span className="text-zinc-400">ACTIVE (0.85)</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span className="text-zinc-300">SSN & PII Anonymizer</span>
                <span className="text-zinc-400">ACTIVE (0.90)</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span className="text-zinc-300">System Leakage Guard</span>
                <span className="text-zinc-400">ACTIVE (0.75)</span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span className="text-zinc-300">HITL Gate</span>
                <span className="text-zinc-400">SCORE &gt; 50</span>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center text-center space-y-1">
              <span className="text-[11px] font-medium text-zinc-400">
                No data to display
              </span>
              <span className="text-[10px] text-zinc-500 max-w-[170px]">
                Try using a different filter selection
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
