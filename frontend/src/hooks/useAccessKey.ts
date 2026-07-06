import { useState, useEffect } from 'react'

const SESSION_KEY = 'narad_access_key'

/**
 * Session-only (sessionStorage) access key, shared across any component that
 * needs to authenticate a write action (hospital reports, parliament trigger).
 * Deliberately NOT localStorage (doesn't persist across browser restarts) and
 * NEVER baked into the build — this is entered by a human each session.
 */
export function useAccessKey() {
  const [accessKey, setAccessKey] = useState(() => sessionStorage.getItem(SESSION_KEY) || '')

  useEffect(() => {
    sessionStorage.setItem(SESSION_KEY, accessKey)
  }, [accessKey])

  return [accessKey, setAccessKey] as const
}
