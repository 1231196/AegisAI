import type { ReactNode } from "react";
import "./PageHeader.css";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="aegis-page-header">
      <div className="aegis-page-header__text">
        <h1 className="aegis-page-header__title">{title}</h1>
        {subtitle && <p className="aegis-page-header__subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="aegis-page-header__actions">{actions}</div>}
    </div>
  );
}
