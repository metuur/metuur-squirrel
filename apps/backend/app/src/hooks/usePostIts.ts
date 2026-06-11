import { useEffect, useState } from "react";
import { api, PostIt } from "../api/client";

export function usePostIts(includeArchived = false) {
  const [data, setData] = useState<PostIt[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const items = await api.postItsList(includeArchived);
      setData(items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load Post-its");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, [includeArchived]);

  return { data, loading, error, refresh, setData };
}
