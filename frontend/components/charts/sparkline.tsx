"use client";

import React from "react";

export function SparklineBadge({
  color = "#d96565",
  direction = "up",
}: {
  color?: string;
  direction?: "up" | "down";
}) {
  return (
    <div className="flex items-center">
      <svg
        width="24"
        height="12"
        viewBox="0 0 24 12"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d={
            direction === "up"
              ? "M1 10L6 8L11 9L16 4L23 2"
              : "M1 2L6 4L11 3L16 8L23 10"
          }
          stroke={color}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}
