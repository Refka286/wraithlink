import { NavLink } from "react-router-dom";
import { BarChart3, KeyRound, LayoutDashboard, Users, Wrench } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
    isActive ? "bg-accent/12 text-accent" : "text-ink-300 hover:bg-ink-700/40 hover:text-ink-50"
  }`;

export function Sidebar() {
  const { user, logout } = useAuth();

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-hairline bg-surface/60">
      <div className="px-5 py-6">
        <span className="text-lg font-extrabold tracking-tight">
          <span className="grad-text">Wraithlink</span>
        </span>
        <p className="mt-1 text-[11px] text-ink-500">Audit offensif pilote par le risque</p>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        <NavLink to="/" end className={navLinkClass}>
          <LayoutDashboard size={17} />
          Engagements
        </NavLink>
        <NavLink to="/outils" className={navLinkClass}>
          <Wrench size={17} />
          Outils
        </NavLink>
        <NavLink to="/statistiques" className={navLinkClass}>
          <BarChart3 size={17} />
          Statistiques
        </NavLink>
        {(user?.role === "admin" || user?.role === "pentester") && (
          <NavLink to="/identifiants" className={navLinkClass}>
            <KeyRound size={17} />
            Identifiants
          </NavLink>
        )}
        {user?.role === "admin" && (
          <NavLink to="/utilisateurs" className={navLinkClass}>
            <Users size={17} />
            Utilisateurs
          </NavLink>
        )}
      </nav>

      {user && (
        <div className="border-t border-hairline p-4">
          <p className="truncate text-xs text-ink-300">{user.email}</p>
          <p className="mb-3 text-[11px] text-ink-500">{user.role}</p>
          <button onClick={logout} className="btn-secondary w-full py-1.5 text-xs">
            deconnexion
          </button>
        </div>
      )}
    </aside>
  );
}
