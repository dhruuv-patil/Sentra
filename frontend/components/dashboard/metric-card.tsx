"use client";

import React from "react";
import { SparklineBadge } from "@/components/charts/sparkline";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  badge?: React.ReactNode;
  showSparkline?: boolean;
  className?: string;
  isModelCard?: boolean;
}

export function MetricCard({
  title,
  value,
  subtitle,
  badge,
  showSparkline = false,
  className,
  isModelCard = false,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        "dark-card p-4 flex flex-col justify-between select-none",
        className
      )}
    >
      {/* Title & Sparkline */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-normal text-zinc-400">
          {title}
        </span>
        {showSparkline && (
          <SparklineBadge direction="up" color="#d96565" />
        )}
        {badge}
      </div>

      {/* Main Value */}
      <div className="flex items-baseline">
        {isModelCard ? (
          <span className="text-[15px] font-mono font-medium text-white truncate">
            {value}
          </span>
        ) : (
          <span className="text-[26px] font-bold text-white tracking-tight font-sans">
            {value}
          </span>
        )}
      </div>

      {/* Optional Subtitle */}
      {subtitle ? (
        <span className="text-[10px] text-zinc-500 font-mono mt-1 truncate">
          {subtitle}
        </span>
      ) : (
        <div className="h-2" />
      )}
    </div>
  );
}
