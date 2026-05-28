import { useCallback, useEffect, useState } from 'react';

/** Minimal SWR-like hook (no caching) — just enough for this app.
 *  Returns { data, error, isLoading, mutate }. mutate() refetches. */
export function useFetch<T>(key: string | null, fetcher: () => Promise<T>) {
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<Error | undefined>(undefined);
  const [isLoading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!key) return;
    setLoading(true);
    setError(undefined);
    try {
      const v = await fetcher();
      setData(v);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoading(false);
    }
    // fetcher intentionally not in deps; we re-run only when `key` changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    load();
  }, [load]);

  return { data, error, isLoading, mutate: load };
}
