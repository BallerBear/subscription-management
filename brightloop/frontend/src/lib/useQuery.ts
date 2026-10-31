"use client";
import { useCallback, useEffect, useState } from "react";
import { apiRequest } from "./api";
import { PREVIEW } from "./preview";

type State<T> = { data?: T; error?: string; loading: boolean };

/**
 * Fetch `path`. In preview mode a failing/missing endpoint falls back to
 * `sample` after a short delay, so loading skeletons are visible in the demo.
 */
export function useQuery<T>(path: string | null, sample?: T) {
  const [state, setState] = useState<State<T>>({ loading: true });

  const load = useCallback(() => {
    if (!path) { setState({ loading: false }); return; } // null path = nothing to fetch
    setState((s) => ({ data: s.data, loading: true }));
    apiRequest<T>(path)
      .then((data) => setState({ data, loading: false }))
      .catch((e: Error) => {
        if (PREVIEW && sample !== undefined) {
          setTimeout(() => setState({ data: sample, loading: false }), 650);
        } else {
          setState({ error: e.message, loading: false });
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path]);

  useEffect(load, [load]);
  return { ...state, refetch: load };
}
