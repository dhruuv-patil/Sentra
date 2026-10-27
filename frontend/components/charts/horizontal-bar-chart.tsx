"use client";

import React from "react";

interface ConnectionUsage {
  name: string;
  provider: string;
  prompts: number;
  raw_count?: number;
  color?: string;
}

interface HorizontalBarChartProps {
  data: ConnectionUsage[];
}

export function HorizontalBarChart({ data }: HorizontalBarChartProps) {
  const maxVal = 8;
  const ticks = [0, 2, 4, 6, 8];

  // Restrained minimal color mapping matching screenshot
  const getColor = (idx: number, fallback?: string) => {
    if (idx === 0) return "#d96565"; // muted coral/salmon
    if (idx === 1) return "#439e73"; // muted sage green
    if (idx === 2) return "#4d78a8"; // muted slate blue
    return fallback || "#5b6bb2";
  };

  return (
    <div className="w-full flex flex-col justify-between select-none">
      <div className="space-y-3">
        {data.slice(0, 3).map((item, idx) => {
          const pct = Math.min((item.prompts / maxVal) * 100, 100);
          return (
            <div key={item.name}>
              <div className="flex items-center justify-between text-[11px] mb-1">
                <span className="text-zinc-300 font-mono text-[10.5px] truncate max-w-[240px]">
                  {item.name}
                </span>
                <span className="text-zinc-500 font-mono text-[10px]">
                  {item.raw_count ? `${item.raw_count.toLocaleString()}` : `${item.prompts}k`}
                </span>
              </div>
              <div className="w-full h-3 bg-[#12192a] rounded-xs overflow-hidden border border-white/[0.04]">
                <div
                  className="h-full rounded-xs transition-all duration-300"
                  style={{
                    width: `${pct}%`,
                    backgroundColor: getColor(idx, item.color),
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* X Axis ticks */}
      <div className="relative w-full mt-4 pt-2 border-t border-white/[0.06]">
        <div className="flex justify-between text-[8.5px] font-mono text-zinc-500 px-0.5">
          {ticks.map((t) => (
            <span key={t}>{t}</span>
          ))}
        </div>
        <div className="text-center text-[9px] text-zinc-500 mt-1 font-normal">
          Number of prompts
        </div>
      </div>
    </div>
  );
}
