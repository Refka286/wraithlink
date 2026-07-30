import { Link, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-ink-900 text-ink-50">
      <header className="border-b border-ink-700 bg-black">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link to="/" className="flex items-baseline gap-2">
            <span className="text-lg font-bold tracking-tight text-red-600">Aegis</span>
            <span className="text-lg font-bold tracking-tight text-blue-500">Pen</span>
          </Link>
          {user && (
            <div className="flex items-center gap-4 text-sm text-ink-300">
              <span>
                {user.email} <span className="text-ink-500">({user.role})</span>
              </span>
              <button
                onClick={logout}
                className="rounded border border-ink-600 px-3 py-1 text-ink-200 hover:border-red-700 hover:text-red-500"
              >
                deconnexion
              </button>
            </div>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
