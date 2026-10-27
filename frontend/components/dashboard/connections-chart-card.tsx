"use client";

import React from "react";
import { HorizontalBarChart } from "@/components/charts/horizontal-bar-chart";
import { cn } from "@/lib/utils";

interface ConnectionUsage {
  name: string;
  provider: string;
  prompts: number;
  raw_count?: number;
  color?: string;
}

interface ConnectionsChartCardProps {
  data?: ConnectionUsage[];
  className?: string;
}

export function ConnectionsChartCard({ data = [], className }: ConnectionsChartCardProps) {
  return (
    <div className={cn("dark-card p-4 flex flex-col justify-between select-none", className)}>
      {/* Title */}
      <div className="text-[11px] font-normal text-zinc-400 mb-2">
        Top 5 connections by usage
      </div>

      <div className="flex-1 flex flex-col justify-center">
        <HorizontalBarChart data={data} />
      </div>
    </div>
  );
}
