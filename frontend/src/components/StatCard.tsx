import { STAT_ICONS } from "./icons";
import type { StatIcon } from "../mocks/data";
import "./StatCard.css";

interface StatCardProps {
  label: string;
  value: string;
  delta?: string;
  deltaDirection?: "up" | "down";
  meta?: string;
  icon: StatIcon;
}

export function StatCard({
  label,
  value,
  delta,
  deltaDirection = "up",
  meta,
  icon,
}: StatCardProps) {
  const Icon = STAT_ICONS[icon];
  return (
    <div className="aegis-stat-card">
      <div className="aegis-stat-card__icon">
        <Icon />
      </div>
      <div className="aegis-stat-card__label">{label}</div>
      <div className="aegis-stat-card__value">{value}</div>
      {(delta || meta) && (
        <div
          className={`aegis-stat-card__meta ${
            delta && deltaDirection === "up" ? "aegis-stat-card__meta--up" : ""
          } ${delta && deltaDirection === "down" ? "aegis-stat-card__meta--down" : ""}`}
        >
          {delta && (
            <span className="aegis-stat-card__delta">
              {deltaDirection === "up" ? "↑" : "↓"} {delta}
            </span>
          )}
          {meta && <span>{meta}</span>}
        </div>
      )}
    </div>
  );
}
