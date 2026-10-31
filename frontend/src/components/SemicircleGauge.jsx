import React from "react";

export function SemicircleGauge({ score = 0, level = "LOW" }) {
  const clamped = Math.min(Math.max(score, 0), 100);
  const radius = 60;
  const strokeWidth = 12;
  // Circumference of semicircle: PI * radius
  const arcLength = Math.PI * radius;
  const offset = arcLength - (arcLength * clamped) / 100;

  const color =
    clamped >= 70 ? "#f43f5e" : clamped >= 40 ? "#f59e0b" : "#10b981";

  return (
    <div className="relative flex flex-col items-center justify-center p-3">
      <svg width="160" height="95" viewBox="0 0 160 95" className="overflow-visible">
        {/* Background track arc */}
        <path
          d="M 20 80 A 60 60 0 0 1 140 80"
          fill="none"
          stroke="#1e293b"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Filled arc */}
        <path
          d="M 20 80 A 60 60 0 0 1 140 80"
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={arcLength}
          strokeDashoffset={offset}
          style={{
            transition: "stroke-dashoffset 0.8s cubic-bezier(0.16, 1, 0.3, 1)",
          }}
        />
      </svg>
      <div className="absolute top-11 flex flex-col items-center text-center">
        <span className="text-3xl font-extrabold tracking-tight text-white leading-none">
          {clamped}
        </span>
        <span className="text-[11px] font-semibold text-slate-400 mt-0.5 tracking-wider uppercase">
          / 100 Score
        </span>
      </div>
    </div>
  );
}

