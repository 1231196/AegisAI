/**
 * Shared inline icon set (1.5 stroke, currentColor) for the pages added
 * alongside the Aegis AI mock. Mirrors the style already used in
 * Sidebar.tsx / PasswordInput.tsx so every icon in the app reads as one
 * family, without pulling in an icon-font/svg-library dependency.
 */
import type { ReactNode } from "react";

type IconProps = { className?: string };

function base(children: ReactNode, className?: string) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export function ActivityIcon({ className }: IconProps) {
  return base(<path d="M2.5 10.5h3.2l2-5.5 3 10 2-6.5h4.6" />, className);
}
export function DocumentIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M5 2.5h7l3.5 3.5v11.5H5z" />
      <path d="M12 2.5v3.5h3.5" />
      <path d="M7.5 11h5M7.5 13.5h5" />
    </>,
    className,
  );
}
export function ChatBubbleIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M3 4h14a1.5 1.5 0 0 1 1.5 1.5v7A1.5 1.5 0 0 1 17 14H8l-4 3v-3H3a1.5 1.5 0 0 1-1.5-1.5v-7A1.5 1.5 0 0 1 3 4z" />
    </>,
    className,
  );
}
export function BuildingStatIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M4 17.5V3.5h8v14" />
      <path d="M12 8.5h4v9" />
      <path d="M6.2 6.5h1.2M6.2 9.5h1.2M6.2 12.5h1.2M9.2 6.5h1.2M9.2 9.5h1.2M9.2 12.5h1.2" />
      <path d="M2.5 17.5h15" />
    </>,
    className,
  );
}
export function ClockIcon({ className }: IconProps) {
  return base(
    <>
      <circle cx="10" cy="10" r="7.2" />
      <path d="M10 6v4l2.6 2" />
    </>,
    className,
  );
}
export function DollarIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M10 2.5v15" />
      <path d="M13.5 5.5c0-1.4-1.6-2.2-3.5-2.2s-3.5.9-3.5 2.4c0 3.2 7 1.6 7 4.8 0 1.6-1.6 2.5-3.5 2.5s-3.7-1-3.7-2.4" />
    </>,
    className,
  );
}
export function TokenIcon({ className }: IconProps) {
  return base(
    <>
      <circle cx="10" cy="10" r="7.2" />
      <path d="M7 10h6M10 7v6" />
    </>,
    className,
  );
}
export function TargetIcon({ className }: IconProps) {
  return base(
    <>
      <circle cx="10" cy="10" r="7" />
      <circle cx="10" cy="10" r="3.6" />
      <circle cx="10" cy="10" r="0.6" fill="currentColor" />
    </>,
    className,
  );
}
export function CpuIcon({ className }: IconProps) {
  return base(
    <>
      <rect x="6" y="6" width="8" height="8" rx="1" />
      <rect x="3" y="9" width="2" height="2" />
      <rect x="15" y="9" width="2" height="2" />
      <rect x="9" y="3" width="2" height="2" />
      <rect x="9" y="15" width="2" height="2" />
    </>,
    className,
  );
}
export function MemoryIcon({ className }: IconProps) {
  return base(
    <>
      <rect x="3" y="5" width="14" height="10" rx="1.2" />
      <path d="M6 8.5h5M6 11.5h8" />
    </>,
    className,
  );
}
export function RequestsIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M3 15V8l4-4.5L11 8v7" />
      <path d="M3 15h8M13 15V6.5l4 3.5v5" />
    </>,
    className,
  );
}
export function ErrorIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M10 3 2.5 16.5h15z" />
      <path d="M10 8v3.4" />
      <circle cx="10" cy="13.6" r="0.6" fill="currentColor" />
    </>,
    className,
  );
}
export function SearchIcon({ className }: IconProps) {
  return base(
    <>
      <circle cx="8.6" cy="8.6" r="5.4" />
      <path d="M16.5 16.5l-3.6-3.6" />
    </>,
    className,
  );
}
export function GridIcon({ className }: IconProps) {
  return base(
    <>
      <rect x="2.5" y="2.5" width="6" height="6" rx="1" />
      <rect x="11.5" y="2.5" width="6" height="6" rx="1" />
      <rect x="2.5" y="11.5" width="6" height="6" rx="1" />
      <rect x="11.5" y="11.5" width="6" height="6" rx="1" />
    </>,
    className,
  );
}
export function HelpIcon({ className }: IconProps) {
  return base(
    <>
      <circle cx="10" cy="10" r="7.2" />
      <path d="M7.8 7.6a2.2 2.2 0 1 1 3.1 2c-.7.4-1.1.9-1.1 1.7v.4" />
      <circle cx="10" cy="14" r="0.6" fill="currentColor" />
    </>,
    className,
  );
}
export function BellIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M5 8.2a5 5 0 0 1 10 0c0 3.6 1.2 4.6 1.2 4.6H3.8S5 11.8 5 8.2z" />
      <path d="M8.2 15.5a1.8 1.8 0 0 0 3.6 0" />
    </>,
    className,
  );
}
export function ChevronDownIcon({ className }: IconProps) {
  return base(<path d="M5 7.5 10 12.5 15 7.5" />, className);
}
export function CloseIcon({ className }: IconProps) {
  return base(<path d="M5 5l10 10M15 5 5 15" />, className);
}
export function PlusIcon({ className }: IconProps) {
  return base(<path d="M10 4v12M4 10h12" />, className);
}
export function SendIcon({ className }: IconProps) {
  return base(<path d="M17 3 2.5 9.2 9 11l1.8 6.5z" />, className);
}
export function UploadIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M10 12.5V3.5M6.5 7 10 3.5 13.5 7" />
      <path d="M3.5 14v1.5A1.5 1.5 0 0 0 5 17h10a1.5 1.5 0 0 0 1.5-1.5V14" />
    </>,
    className,
  );
}
export function CheckIcon({ className }: IconProps) {
  return base(<path d="M4 10.5 8 14.5 16 5.5" />, className);
}
export function MoreIcon({ className }: IconProps) {
  return base(
    <>
      <circle cx="4.5" cy="10" r="1" fill="currentColor" stroke="none" />
      <circle cx="10" cy="10" r="1" fill="currentColor" stroke="none" />
      <circle cx="15.5" cy="10" r="1" fill="currentColor" stroke="none" />
    </>,
    className,
  );
}
export function FilterIcon({ className }: IconProps) {
  return base(<path d="M3 4.5h14L11.5 11v5L8.5 14v-3z" />, className);
}
export function ChevronRightIcon({ className }: IconProps) {
  return base(<path d="M7.5 5 12.5 10 7.5 15" />, className);
}
export function ChevronLeftIcon({ className }: IconProps) {
  return base(<path d="M12.5 5 7.5 10 12.5 15" />, className);
}
export function ZoomInIcon({ className }: IconProps) {
  return base(
    <>
      <circle cx="8.6" cy="8.6" r="5.4" />
      <path d="M16.5 16.5l-3.6-3.6" />
      <path d="M8.6 6.4v4.4M6.4 8.6h4.4" />
    </>,
    className,
  );
}
export function PlugIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M12.4 4.6a2.6 2.6 0 0 1 3.6 3.6l-1 1-3.6-3.6z" />
      <path d="M11 6l-6.5 6.5a2 2 0 1 0 2.8 2.8L14 8.5" />
      <path d="M4 16l1.2-1.2" />
    </>,
    className,
  );
}
export function TicketPlusIcon({ className }: IconProps) {
  return base(
    <>
      <path d="M3 6.5V4h14v2.5a2 2 0 0 0 0 4V13a2 2 0 0 0 0 4V19H3v-2a2 2 0 0 0 0-4v-2.5a2 2 0 0 0 0-4z" />
      <path d="M9 4v12" />
    </>,
    className,
  );
}

export const STAT_ICONS = {
  activity: ActivityIcon,
  document: DocumentIcon,
  chat: ChatBubbleIcon,
  building: BuildingStatIcon,
  clock: ClockIcon,
  dollar: DollarIcon,
  token: TokenIcon,
  target: TargetIcon,
  cpu: CpuIcon,
  memory: MemoryIcon,
  requests: RequestsIcon,
  error: ErrorIcon,
} as const;
