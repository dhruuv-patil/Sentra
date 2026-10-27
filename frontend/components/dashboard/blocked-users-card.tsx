"use client";

import React from "react";
import { ArrowUp, ArrowDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface BlockedUser {
  rank: number;
  user_id: string;
  blocked: number;
  trend: "up" | "down";
  change?: string;
}

interface BlockedUsersCardProps {
  users?: BlockedUser[];
  className?: string;
}

export function BlockedUsersCard({ users = [], className }: BlockedUsersCardProps) {
  return (
    <div className={cn("dark-card p-4 flex flex-col justify-between select-none", className)}>
      {/* Title */}
      <div className="text-[11px] font-normal text-zinc-400 mb-2.5">
        Most blocked prompts per user
      </div>

      {/* User List */}
      <div className="space-y-1.5 flex-1 flex flex-col justify-between">
        {users.map((u) => {
          const isUp = u.trend === "up";
          return (
            <div
              key={u.rank}
              className="flex items-center justify-between px-2.5 py-1.5 rounded bg-[#12192a] border border-white/[0.04]"
            >
              {/* Left: Rank & User Identifier */}
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-[11px] font-mono text-zinc-400">
                  {u.rank}.
                </span>
                <span className="text-[11.5px] font-mono text-zinc-200 truncate">
                  {u.user_id}
                </span>
              </div>

              {/* Right: Blocked Count & Arrow */}
              <div className="flex items-center gap-1.5">
                <span className="text-[11.5px] font-mono font-medium text-white">
                  {u.blocked.toLocaleString()}
                </span>
                {isUp ? (
                  <ArrowUp className="w-3 h-3 text-zinc-400" />
                ) : (
                  <ArrowDown className="w-3 h-3 text-[#d96565]" />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
