import { useAuth } from "../hooks/useAuth";

export function HomePage() {
  const { person, logout } = useAuth();
  if (!person) return null;

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      <header className="flex items-center justify-between border-b border-neutral-800 px-6 py-4">
        <span className="font-semibold">Shared World</span>
        <div className="flex items-center gap-3">
          {person.avatar_url && (
            <img src={person.avatar_url} alt="" className="h-8 w-8 rounded-full" />
          )}
          <span className="text-sm text-neutral-300">{person.username}</span>
          <button
            type="button"
            onClick={() => void logout()}
            className="rounded-md border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800"
          >
            Log out
          </button>
        </div>
      </header>
      <main className="p-6 text-neutral-400">
        Logged in. Master data and session entry screens land in Phase 1.
      </main>
    </div>
  );
}
