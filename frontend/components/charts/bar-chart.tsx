"use client";

import React, { useState } from "react";

interface BarDataPoint {
  label: string;
  prompts_sent: number;
  blocked_prompts: number;
  blocked_responses: number;
}

interface BarChartProps {
  data: BarDataPoint[];
  height?: number;
}

export function GroupedBarChart({ data, height = 150 }: BarChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const maxValue = 4000;
  const chartHeight = height - 35;
  const chartWidth = 360;
  const paddingLeft = 32;
  const paddingRight = 10;
  const plotWidth = chartWidth - paddingLeft - paddingRight;

  const yTicks = [0, 1000, 2000, 3000, 4000];

  return (
    <div className="relative w-full flex flex-col items-center select-none">
      <svg
        viewBox={`0 0 ${chartWidth} ${height}`}
        className="w-full h-auto max-h-[170px] overflow-visible"
      >
        {/* Y Axis Gridlines & Labels */}
        {yTicks.map((val) => {
          const y = chartHeight - (val / maxValue) * chartHeight + 8;
          return (
            <g key={val}>
              <line
                x1={paddingLeft}
                y1={y}
                x2={chartWidth - paddingRight}
                y2={y}
                stroke="rgba(255, 255, 255, 0.04)"
              />
              <text
                x={paddingLeft - 5}
                y={y + 3}
                fill="rgba(255, 255, 255, 0.3)"
                fontSize="7.5"
                fontFamily="ui-monospace, monospace"
                textAnchor="end"
              >
                {val === 0 ? "0" : val.toLocaleString()}
              </text>
            </g>
          );
        })}

        {/* Bars */}
        {data.map((item, idx) => {
          const groupWidth = plotWidth / data.length;
          const groupX = paddingLeft + idx * groupWidth;
          const barWidth = 6;
          const gap = 1.5;

          const sentHeight = (Math.min(item.prompts_sent, maxValue) / maxValue) * chartHeight;
          const blockedHeight = (Math.min(item.blocked_prompts, maxValue) / maxValue) * chartHeight;
          const respHeight = (Math.min(item.blocked_responses * 40, maxValue) / maxValue) * chartHeight;

          const xSent = groupX + (groupWidth - (barWidth * 3 + gap * 2)) / 2;
          const xBlocked = xSent + barWidth + gap;
          const xResp = xBlocked + barWidth + gap;

          const ySent = chartHeight - sentHeight + 8;
          const yBlocked = chartHeight - blockedHeight + 8;
          const yResp = chartHeight - respHeight + 8;

          const isHovered = hoveredIdx === idx;

          return (
            <g
              key={item.label}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              className="cursor-pointer"
            >
              {isHovered && (
                <rect
                  x={groupX}
                  y={8}
                  width={groupWidth}
                  height={chartHeight}
                  fill="rgba(255, 255, 255, 0.02)"
                  rx="2"
                />
              )}

              {/* Sent Bar - Muted Slate/Blue */}
              <rect
                x={xSent}
                y={ySent}
                width={barWidth}
                height={sentHeight}
                fill="#5b6bb2"
                rx="1"
              />

              {/* Blocked Prompts Bar - Muted Coral/Red */}
              <rect
                x={xBlocked}
                y={yBlocked}
                width={barWidth}
                height={blockedHeight}
                fill="#d96565"
                rx="1"
              />

              {/* Blocked Responses Bar - Muted Amber */}
              {respHeight > 0 && (
                <rect
                  x={xResp}
                  y={yResp}
                  width={barWidth}
                  height={respHeight}
                  fill="#c4923e"
                  rx="1"
                />
              )}

              {/* X Axis Label */}
              <text
                x={groupX + groupWidth / 2}
                y={chartHeight + 18}
                fill={isHovered ? "#ffffff" : "rgba(255, 255, 255, 0.35)"}
                fontSize="7"
                fontFamily="Inter, sans-serif"
                textAnchor="end"
                transform={`rotate(-40, ${groupX + groupWidth / 2}, ${chartHeight + 18})`}
              >
                {item.label}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Hover Tooltip */}
      {hoveredIdx !== null && data[hoveredIdx] && (
        <div className="absolute top-0 right-1 bg-[#12192a] border border-white/10 px-2 py-1 rounded text-[10px] shadow pointer-events-none z-10 font-mono">
          <div className="text-zinc-300 font-semibold mb-0.5 border-b border-white/10 pb-0.5">
            {data[hoveredIdx].label}
          </div>
          <div className="text-zinc-400">
            Sent: <span className="text-white">{data[hoveredIdx].prompts_sent.toLocaleString()}</span>
          </div>
          <div className="text-zinc-400">
            Blocked: <span className="text-[#d96565]">{data[hoveredIdx].blocked_prompts.toLocaleString()}</span>
          </div>
          <div className="text-zinc-400">
            Responses: <span className="text-[#c4923e]">{data[hoveredIdx].blocked_responses}</span>
          </div>
        </div>
      )}

      {/* Legend matching screenshot */}
      <div className="flex items-center justify-center gap-3 mt-1 text-[8.5px] text-zinc-400 select-none">
        <div className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-xs bg-[#5b6bb2]" />
          <span>Prompts Sent</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-xs bg-[#d96565]" />
          <span>Blocked Prompts</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-xs bg-[#c4923e]" />
          <span>Blocked Responses</span>
        </div>
      </div>
    </div>
  );
}
