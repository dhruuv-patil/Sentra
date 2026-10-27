"use client";

import React from "react";
import { MultiLineChart } from "@/components/charts/line-chart";
import { cn } from "@/lib/utils";

interface LatencyPoint {
  date: string;
  anthropic: number;
  openai: number;
  groq: number;
  ollama?: number;
}

interface LatencyChartCardProps {
  data?: LatencyPoint[];
  className?: string;
}

export function LatencyChartCard({ data = [], className }: LatencyChartCardProps) {
  return (
    <div className={cn("dark-card p-4 flex flex-col justify-between select-none", className)}>
      {/* Title */}
      <div className="text-[11px] font-normal text-zinc-400 mb-2">
        Latency per LLM provider
      </div>

      <div className="flex-1 flex flex-col justify-center">
        <MultiLineChart data={data} height={145} />
      </div>
    </div>
  );
}
