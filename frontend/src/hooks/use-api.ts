import { useState, useEffect, useCallback, useRef } from 'react'

interface UseApiResult<T> {
  data: T | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  options?: { debounceMs?: number }
): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const doFetch = useCallback(() => {
    // 前リクエストをキャンセル
    if (abortRef.current) {
      abortRef.current.abort()
    }
    const controller = new AbortController()
    abortRef.current = controller

    setLoading(true)
    setError(null)
    fetcher()
      .then((result) => {
        if (!controller.signal.aborted) {
          setData(result)
        }
      })
      .catch((e: Error) => {
        if (!controller.signal.aborted) {
          setError(e.message)
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    const debounceMs = options?.debounceMs
    if (debounceMs && debounceMs > 0) {
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(doFetch, debounceMs)
    } else {
      doFetch()
    }

    return () => {
      if (abortRef.current) {
        abortRef.current.abort()
      }
      if (timerRef.current) {
        clearTimeout(timerRef.current)
      }
    }
  }, [doFetch, options?.debounceMs])

  return { data, loading, error, refetch: doFetch }
}
