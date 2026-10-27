"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ShieldAlert,
  Terminal,
  MessageSquare,
  KeyRound,
  Network,
  FileCode2,
  Settings2,
  BookOpen,
  Search,
  Scale,
  ChevronLeft,
  ChevronRight,
  Layers,
} from "lucide-react";
import { Brand, LogoMark } from "@/components/brand/logo";
import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

interface NavSection {
  title?: string;
  items: NavItem[];
}

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const navigation: NavSection[] = [
    {
      items: [
        {
          label: "Dashboard",
          href: "/",
          icon: LayoutDashboard,
        },
      ],
    },
    {
      title: "AI GUARDRAILS",
      items: [
        {
          label: "Projects",
          href: "/projects",
          icon: Layers,
        },
        {
          label: "Guardrails",
          href: "/guardrails",
          icon: ShieldAlert,
        },
        {
          label: "Playground",
          href: "/playground",
          icon: Terminal,
        },
        {
          label: "Chat",
          href: "/chat",
          icon: MessageSquare,
        },
        {
          label: "Approvals",
          href: "/approvals",
          icon: Scale,
        },
      ],
    },
    {
      title: "CONFIGURE",
      items: [
        {
          label: "API tokens",
          href: "/tokens",
          icon: KeyRound,
        },
        {
          label: "Connections",
          href: "/connections",
          icon: Network,
        },
        {
          label: "Logs",
          href: "/logs",
          icon: FileCode2,
        },
        {
          label: "Settings",
          href: "/settings",
          icon: Settings2,
        },
        {
          label: "API docs",
          href: "/docs",
          icon: BookOpen,
        },
      ],
    },
  ];

  return (
    <aside
      className={cn(
        "relative flex flex-col h-screen select-none bg-[#070a12] border-r border-white/[0.06] transition-all duration-200 z-30 shrink-0",
        collapsed ? "w-[64px]" : "w-[230px]"
      )}
    >
      {/* Top Header */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-white/[0.06]">
        {collapsed ? (
          <div className="mx-auto cursor-pointer" onClick={() => setCollapsed(false)}>
            <LogoMark className="w-5 h-5" />
          </div>
        ) : (
          <Link href="/" className="flex items-center gap-2">
            <Brand subtitle="Security Gateway" />
          </Link>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-zinc-500 hover:text-zinc-300 p-1 rounded hover:bg-white/[0.03] transition-colors ml-auto"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Search Input Box */}
      {!collapsed && (
        <div className="p-3 pb-1">
          <div className="relative flex items-center w-full">
            <Search className="absolute left-2.5 w-3.5 h-3.5 text-zinc-500 pointer-events-none" />
            <input
              type="text"
              placeholder="Search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-8 pl-8 pr-2.5 text-[12px] bg-[#0e1422] text-zinc-200 placeholder-zinc-500 rounded border border-white/[0.06] focus:outline-none focus:border-white/20 transition-colors"
            />
          </div>
        </div>
      )}

      {/* Navigation Groups */}
      <div className="flex-1 overflow-y-auto px-2 space-y-3 py-2">
        {navigation.map((section, sIdx) => {
          const visibleItems = section.items.filter((item) =>
            searchQuery
              ? item.label.toLowerCase().includes(searchQuery.toLowerCase())
              : true
          );

          if (visibleItems.length === 0) return null;

          return (
            <div key={sIdx} className="space-y-0.5">
              {section.title && !collapsed && (
                <div className="px-2.5 py-1 text-[10px] font-medium text-zinc-500 tracking-wider uppercase">
                  {section.title}
                </div>
              )}
              {visibleItems.map((item) => {
                const isActive =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);
                const Icon = item.icon;

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-2.5 px-2.5 py-1.5 rounded text-[12px] transition-colors group",
                      isActive
                        ? "bg-white/[0.08] text-white font-medium"
                        : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03]"
                    )}
                    title={collapsed ? item.label : undefined}
                  >
                    <Icon
                      className={cn(
                        "w-4 h-4 shrink-0 transition-colors",
                        isActive
                          ? "text-white"
                          : "text-zinc-400 group-hover:text-zinc-200"
                      )}
                    />
                    {!collapsed && (
                      <span className="truncate">{item.label}</span>
                    )}
                  </Link>
                );
              })}
            </div>
          );
        })}
      </div>

      {/* Bottom Status */}
      <div className="p-3 border-t border-white/[0.06] bg-[#06080e]">
        {!collapsed ? (
          <div className="flex flex-col min-w-0">
            <span className="text-[11px] font-medium text-zinc-300 truncate">
              Gateway Engine
            </span>
            <span className="text-[9.5px] text-zinc-500 font-mono">
              Port 8000 • Operational
            </span>
          </div>
        ) : (
          <div className="w-2 h-2 mx-auto rounded-full bg-white/20" />
        )}
      </div>
    </aside>
  );
}
