"use client";

import React, { useState } from "react";

interface LatencyPoint {
  date: string;
  anthropic: number;
  openai: number;
  groq: number;
  ollama?: number;
}

interface LineChartProps {
  data: LatencyPoint[];
  height?: number;
}

export function MultiLineChart({ data, height = 150 }: LineChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const maxVal = 15000;
  const chartWidth = 360;
  const chartHeight = height - 35;
  const paddingLeft = 38;
  const paddingRight = 10;
  const plotWidth = chartWidth - paddingLeft - paddingRight;

  const yTicks = [0, 5000, 10000, 15000];

  const getX = (idx: number) => paddingLeft + (idx / Math.max(data.length - 1, 1)) * plotWidth;
  const getY = (val: number) => chartHeight - (Math.min(val, maxVal) / maxVal) * chartHeight + 8;

  const generatePath = (key: "anthropic" | "openai") => {
    return data
      .map((d, i) => `${i === 0 ? "M" : "L"} ${getX(i).toFixed(1)} ${getY(d[key]).toFixed(1)}`)
      .join(" ");
  };

  const anthropicPath = generatePath("anthropic");
  const openaiPath = generatePath("openai");

  return (
    <div className="relative w-full flex flex-col items-center select-none">
      <svg
        viewBox={`0 0 ${chartWidth} ${height}`}
        className="w-full h-auto max-h-[170px] overflow-visible"
      >
        {/* Y Axis Gridlines & Labels */}
        {yTicks.map((val) => {
          const y = getY(val);
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
                x={paddingLeft - 6}
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

        {/* Vertical Y-axis label */}
        <text
          x={-chartHeight / 2 - 4}
          y={10}
          transform="rotate(-90)"
          fill="rgba(255, 255, 255, 0.35)"
          fontSize="7"
          fontFamily="Inter, sans-serif"
          textAnchor="middle"
        >
          Avg. Response Time (ms)
        </text>

        {/* Anthropic Line - Muted Green */}
        <path
          d={anthropicPath}
          fill="none"
          stroke="#439e73"
          strokeWidth="1.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* OpenAI Line - Muted Terracotta/Orange */}
        <path
          d={openaiPath}
          fill="none"
          stroke="#d97746"
          strokeWidth="1.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Points & X-axis Labels */}
        {data.map((d, i) => {
          const x = getX(i);
          const isHovered = hoveredIdx === i;

          return (
            <g
              key={d.date}
              onMouseEnter={() => setHoveredIdx(i)}
              onMouseLeave={() => setHoveredIdx(null)}
              className="cursor-pointer"
            >
              {isHovered && (
                <line
                  x1={x}
                  y1={8}
                  x2={x}
                  y2={chartHeight + 8}
                  stroke="rgba(255, 255, 255, 0.15)"
                  strokeDasharray="2 2"
                />
              )}

              {/* X Axis Label */}
              <text
                x={x}
                y={chartHeight + 18}
                fill={isHovered ? "#ffffff" : "rgba(255, 255, 255, 0.35)"}
                fontSize="7"
                fontFamily="Inter, sans-serif"
                textAnchor="middle"
              >
                {d.date}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Hover Tooltip */}
      {hoveredIdx !== null && data[hoveredIdx] && (
        <div className="absolute top-0 right-1 bg-[#12192a] border border-white/10 px-2 py-1 rounded text-[10px] shadow pointer-events-none z-10 font-mono">
          <div className="text-zinc-300 font-semibold mb-0.5 border-b border-white/10 pb-0.5">
            {data[hoveredIdx].date}
          </div>
          <div className="text-zinc-400">
            Anthropic: <span className="text-[#439e73]">{data[hoveredIdx].anthropic} ms</span>
          </div>
          <div className="text-zinc-400">
            OpenAI: <span className="text-[#d97746]">{data[hoveredIdx].openai} ms</span>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-1 text-[8.5px] text-zinc-400 select-none">
        <div className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-xs bg-[#439e73]" />
          <span>anthropic</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-xs bg-[#d97746]" />
          <span>openai</span>
        </div>
      </div>
    </div>
  );
}
