import { useCallback, useEffect, useRef, useState } from 'react';

/** Minimal SWR-like hook (no caching) — just enough for this app.
 *  Returns { data, error, isLoading, mutate }. mutate() refetches. */
export function useFetch<T>(key: string | null, fetcher: () => Promise<T>) {
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<Error | undefined>(undefined);
  const [isLoading, setLoading] = useState(false);
  // Generation counter: each load (and unmount) bumps it, so a slow stale
  // response can't overwrite newer data or set state after unmount. The
  // fetchers are arbitrary promises, so AbortController can't be threaded
  // through — ignoring superseded results is the equivalent guard.
  const genRef = useRef(0);

  const load = useCallback(async () => {
    if (!key) return;
    const gen = ++genRef.current;
    setLoading(true);
    setError(undefined);
    try {
      const v = await fetcher();
      if (gen === genRef.current) setData(v);
    } catch (e) {
      if (gen === genRef.current) setError(e as Error);
    } finally {
      if (gen === genRef.current) setLoading(false);
    }
    // fetcher intentionally not in deps; we re-run only when `key` changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    load();
    return () => {
      genRef.current += 1;
    };
  }, [load]);

  return { data, error, isLoading, mutate: load };
}
