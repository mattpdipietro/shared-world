import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, apiFetch } from "../lib/api";
import type { Person } from "../lib/types";

const ME_QUERY_KEY = ["auth", "me"];

/**
 * Current logged-in person, backed by `GET /auth/me`. A 401 means "not
 * logged in" rather than an error, so it resolves to `person: null` instead
 * of surfacing a query error.
 */
export function useAuth() {
  const queryClient = useQueryClient();

  const { data: person, isLoading } = useQuery<Person | null>({
    queryKey: ME_QUERY_KEY,
    queryFn: async () => {
      try {
        return await apiFetch<Person>("/auth/me");
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          return null;
        }
        throw error;
      }
    },
    retry: false,
  });

  async function logout() {
    await apiFetch("/auth/logout", { method: "POST" });
    queryClient.setQueryData(ME_QUERY_KEY, null);
  }

  return { person: person ?? null, isLoading, logout };
}
