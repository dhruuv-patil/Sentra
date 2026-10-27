"use client";

import React, { useState } from "react";
import {
  Calendar,
  Filter,
  Info,
  ChevronDown,
  RotateCcw,
  Check,
} from "lucide-react";
import { toast } from "sonner";

interface HeaderProps {
  title?: string;
  selectedRange?: string;
  onRangeChange?: (range: string) => void;
}

export function Header({
  title = "Dashboard",
  selectedRange = "10월 06일/25년 - 4월 07일/26년",
  onRangeChange,
}: HeaderProps) {
  const [filterMenuOpen, setFilterMenuOpen] = useState(false);
  const [clearingCache, setClearingCache] = useState(false);

  const ranges = [
    { label: "Past 24 Hours", value: "24h" },
    { label: "Past 7 Days", value: "7d" },
    { label: "Past 30 Days", value: "30d" },
    { label: "10월 06일/25년 - 4월 07일/26년", value: "screenshot_range" },
    { label: "All Time", value: "all" },
  ];

  const handleClearCache = async () => {
    try {
      setClearingCache(true);
      const res = await fetch("/api/py/cache/clear", { method: "POST" });
      if (res.ok) {
        toast.success("Response cache cleared");
      } else {
        toast.error("Failed to clear cache");
      }
    } catch {
      toast.info("Cache reset locally");
    } finally {
      setClearingCache(false);
    }
  };

  return (
    <header className="h-14 w-full flex items-center justify-between px-6 border-b border-white/[0.06] bg-[#090d16] sticky top-0 z-20">
      {/* Title */}
      <div className="flex items-center gap-3">
        <h1 className="text-[16px] font-medium text-white tracking-tight">
          {title}
        </h1>
      </div>

      {/* Date Filter & Actions */}
      <div className="flex items-center gap-3">
        {/* Filter Pill */}
        <div className="relative flex items-center bg-[#0e1422] border border-white/[0.08] rounded text-[11.5px] select-none">
          <button
            onClick={() => setFilterMenuOpen(!filterMenuOpen)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-zinc-300 hover:text-white border-r border-white/[0.08] transition-colors"
            title="Filter options"
          >
            <Filter className="w-3.5 h-3.5 text-zinc-400" />
            <span className="font-medium text-[11px]">Filter</span>
            <Info className="w-3 h-3 text-zinc-500" />
          </button>

          <button
            onClick={() => setFilterMenuOpen(!filterMenuOpen)}
            className="flex items-center gap-2 px-3 py-1.5 text-zinc-300 hover:text-white transition-colors"
          >
            <Calendar className="w-3.5 h-3.5 text-zinc-400" />
            <span className="font-mono text-[11px]">{selectedRange}</span>
            <ChevronDown className="w-3 h-3 text-zinc-500" />
          </button>

          {/* Filter Dropdown */}
          {filterMenuOpen && (
            <div className="absolute top-full right-0 mt-1.5 w-60 bg-[#0e1422] border border-white/[0.12] rounded shadow-xl p-1 z-50">
              <div className="text-[10px] font-medium text-zinc-500 px-2.5 py-1 uppercase tracking-wider">
                Select Time Window
              </div>
              {ranges.map((r) => {
                const isSelected = selectedRange === r.label || selectedRange.includes(r.label);
                return (
                  <button
                    key={r.value}
                    onClick={() => {
                      onRangeChange?.(r.label);
                      setFilterMenuOpen(false);
                      toast.info(`Filtered: ${r.label}`);
                    }}
                    className="w-full flex items-center justify-between px-2.5 py-1.5 rounded text-left text-[11.5px] text-zinc-300 hover:text-white hover:bg-white/[0.05] transition-colors"
                  >
                    <span>{r.label}</span>
                    {isSelected && <Check className="w-3.5 h-3.5 text-zinc-200" />}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Clear Cache Button */}
        <button
          onClick={handleClearCache}
          disabled={clearingCache}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] text-zinc-400 hover:text-zinc-200 bg-[#0e1422] hover:bg-white/[0.04] border border-white/[0.08] rounded transition-colors"
          title="Clear Response Cache"
        >
          <RotateCcw className={`w-3.5 h-3.5 ${clearingCache ? "animate-spin" : ""}`} />
          <span className="hidden sm:inline">Purge Cache</span>
        </button>
      </div>
    </header>
  );
}
