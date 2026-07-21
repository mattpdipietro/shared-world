import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { person, isLoading } = useAuth();

  if (isLoading) return null;
  if (!person) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
