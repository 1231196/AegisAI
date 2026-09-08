import type { UserResponse } from "../api/client";
import { BellIcon, ChevronDownIcon, GridIcon, HelpIcon, SearchIcon } from "./icons";
import "./Topbar.css";

interface TopbarProps {
  user?: UserResponse | null;
}

/**
 * Visual-only top bar shared by every authenticated screen. Search,
 * icon buttons, and the org pill are decorative for this pass — no
 * network calls, no dropdown wiring.
 */
export function Topbar({ user: _user }: TopbarProps) {
  // Organisation display name isn't part of UserResponse today (only
  // organization_id) — using a static label until the org-name endpoint
  // is wired up. Kept as a prop so the caller can pass the live user
  // once that's available without touching this component's shape.
  const orgLabel = "Acme Corporation";

  return (
    <div className="aegis-topbar">
      <label className="aegis-topbar__search">
        <SearchIcon className="aegis-topbar__search-icon" />
        <input type="text" placeholder="Search anything..." />
        <span className="aegis-topbar__kbd">⌘K</span>
      </label>

      <div className="aegis-topbar__right">
        <button type="button" className="aegis-topbar__icon-btn" title="Apps">
          <GridIcon />
        </button>
        <button type="button" className="aegis-topbar__icon-btn" title="Help">
          <HelpIcon />
        </button>
        <button type="button" className="aegis-topbar__icon-btn" title="Notifications">
          <BellIcon />
        </button>
        <div className="aegis-topbar__divider" aria-hidden="true" />
        <button type="button" className="aegis-topbar__org">
          <span className="aegis-topbar__org-avatar">{orgLabel.charAt(0)}</span>
          <span className="aegis-topbar__org-name">{orgLabel}</span>
          <ChevronDownIcon className="aegis-topbar__org-chevron" />
        </button>
      </div>
    </div>
  );
}
