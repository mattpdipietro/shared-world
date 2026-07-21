import { Navigate } from "react-router-dom";
import { goToDiscordLogin } from "../lib/api";
import { useAuth } from "../hooks/useAuth";

export function LoginPage() {
  const { person, isLoading } = useAuth();

  if (isLoading) return null;
  if (person) return <Navigate to="/" replace />;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-neutral-950 text-neutral-100">
      <div className="text-center">
        <h1 className="text-3xl font-semibold">Shared World</h1>
        <p className="mt-2 text-neutral-400">Sign in to log sessions and track your campaign.</p>
      </div>
      <button
        type="button"
        onClick={goToDiscordLogin}
        className="rounded-md bg-[#5865F2] px-6 py-3 font-medium text-white hover:bg-[#4752c4]"
      >
        Log in with Discord
      </button>
    </div>
  );
}
