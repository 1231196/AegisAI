import { useId } from "react";
import "./Sparkline.css";

interface SparklineProps {
  points: number[];
  variant?: "line" | "area";
  width?: number;
  height?: number;
  className?: string;
}

/**
 * Minimal hand-rolled SVG line/area chart driven by a plain number
 * array. Kept dependency-free (no chart library) since it only ever
 * renders static mock series for Monitoring's mini-charts and
 * Analytics' hero chart.
 */
export function Sparkline({
  points,
  variant = "line",
  width = 120,
  height = 36,
  className,
}: SparklineProps) {
  const gradientId = useId();
  if (points.length < 2) return null;

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const stepX = width / (points.length - 1);

  const coords = points.map((p, i) => {
    const x = i * stepX;
    const y = height - ((p - min) / range) * height;
    return [x, y] as const;
  });

  const linePath = coords
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`)
    .join(" ");
  const areaPath = `${linePath} L${width},${height} L0,${height} Z`;

  return (
    <svg
      className={`aegis-sparkline ${className || ""}`}
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {variant === "area" && (
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--brand-yellow)" stopOpacity="0.35" />
            <stop offset="100%" stopColor="var(--brand-yellow)" stopOpacity="0" />
          </linearGradient>
        </defs>
      )}
      {variant === "area" && <path d={areaPath} fill={`url(#${gradientId})`} stroke="none" />}
      <path d={linePath} fill="none" stroke="var(--brand-yellow)" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
