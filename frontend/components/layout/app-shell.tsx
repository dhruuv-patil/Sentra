"use client";

import React from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { Toaster } from "sonner";

interface AppShellProps {
  children: React.ReactNode;
  title?: string;
  selectedRange?: string;
  onRangeChange?: (range: string) => void;
}

export function AppShell({
  children,
  title = "Dashboard",
  selectedRange,
  onRangeChange,
}: AppShellProps) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#090d16] text-white">
      {/* Sleek Dark Minimal Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden relative">
        <Header
          title={title}
          selectedRange={selectedRange}
          onRangeChange={onRangeChange}
        />

        {/* Scrollable Page Body */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-5 bg-[#090d16]">
          <div className="max-w-[1400px] mx-auto w-full">
            {children}
          </div>
        </main>
      </div>

      <Toaster
        theme="dark"
        position="bottom-right"
        toastOptions={{
          style: {
            background: "#0e1422",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            color: "#f8fafc",
            fontSize: "12px",
          },
        }}
      />
    </div>
  );
}
