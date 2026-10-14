import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';

/** Router transitions are asynchronous; compose rapid edits against the current URL. */
export function useUrlState() {
  const [params, setParams] = useSearchParams();
  const update = useCallback(
    (edit: (next: URLSearchParams) => void, replace = true) => {
      const next = new URLSearchParams(window.location.search);
      edit(next);
      setParams(next, { replace });
    },
    [setParams],
  );
  return [params, update] as const;
}
