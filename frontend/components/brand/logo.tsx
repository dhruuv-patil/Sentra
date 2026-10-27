"use client";

import React from "react";

export function LogoMark({ className = "w-6 h-6" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 36 36"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Outer subtle shield outline */}
      <path
        d="M18 3L30 8.5V18.5C30 25.5 24.5 30.5 18 32.5C11.5 30.5 6 25.5 6 18.5V8.5L18 3Z"
        fill="#0e1422"
        stroke="rgba(255, 255, 255, 0.15)"
        strokeWidth="1.2"
      />

      {/* Clean minimal trident icon */}
      <path
        d="M12 12.5L18 18.5M24 12.5L18 18.5M18 18.5V26"
        stroke="#cbd5e1"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="12.5" r="1.5" fill="#94a3b8" />
      <circle cx="24" cy="12.5" r="1.5" fill="#94a3b8" />
      <circle cx="18" cy="18.5" r="1.5" fill="#ffffff" />
    </svg>
  );
}

export function Brand({
  showText = true,
  subtitle = "AI Guardrail",
}: {
  showText?: boolean;
  subtitle?: string;
}) {
  return (
    <div className="flex items-center gap-2.5 group cursor-pointer select-none">
      <div className="p-1 rounded bg-white/[0.04] border border-white/[0.08] group-hover:border-white/20 transition-colors">
        <LogoMark className="w-5 h-5" />
      </div>
      {showText && (
        <div className="flex flex-col">
          <div className="flex items-center gap-1.5">
            <span className="text-[13px] font-medium tracking-tight text-white">
              F5 AI Guardrail
            </span>
          </div>
          <span className="text-[10px] text-zinc-500 font-mono tracking-wider">
            {subtitle}
          </span>
        </div>
      )}
    </div>
  );
}
