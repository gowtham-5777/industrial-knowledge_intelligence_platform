"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchSessionCheck } from "@/lib/auth";

/** Demonstrates authenticated TanStack Query against the API. */
export function useSessionCheck(enabled = true) {
  return useQuery({
    queryKey: ["session", "check"],
    queryFn: fetchSessionCheck,
    enabled,
    retry: false,
  });
}
