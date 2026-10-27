"use client";

import React from "react";
import { ArrowUpRight } from "lucide-react";
import { GroupedBarChart } from "@/components/charts/bar-chart";
import { cn } from "@/lib/utils";

interface PromptsBlockedCardProps {
  percentage?: number;
  data?: Array<{
    label: string;
    prompts_sent: number;
    blocked_prompts: number;
    blocked_responses: number;
  }>;
  className?: string;
}

export function PromptsBlockedCard({
  percentage = 99,
  data = [],
  className,
}: PromptsBlockedCardProps) {
  return (
    <div className={cn("dark-card p-4 flex flex-col justify-between select-none", className)}>
      {/* Title */}
      <div className="text-[11px] font-normal text-zinc-400 mb-2">
        Prompts sent and blocked
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center flex-1">
        {/* Left Side: Stat */}
        <div className="md:col-span-4 flex flex-col justify-center">
          <div className="flex items-center gap-1.5">
            <span className="text-[38px] font-bold text-white tracking-tight leading-none font-sans">
              {percentage}%
            </span>
            <span className="text-zinc-400">
              <ArrowUpRight className="w-5 h-5 stroke-[2]" />
            </span>
          </div>
          <span className="text-[11px] text-zinc-400 mt-2 font-normal">
            Prompts sent are blocked
          </span>
        </div>

        {/* Right Side: Grouped Bar Chart */}
        <div className="md:col-span-8 flex justify-end">
          <GroupedBarChart data={data} height={145} />
        </div>
      </div>
    </div>
  );
}
