const BASE = '/api'

export async function api(path, options = {}) {
  const resp = await fetch(`${BASE}/${path}`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    ...options,
  })
  if (resp.status === 401) {
    const { useAuthStore } = await import('../stores/auth')
    useAuthStore().logout()
    throw new Error('Unauthorized')
  }
  return resp.json()
}

export async function apiRaw(path, options = {}) {
  const resp = await fetch(`${BASE}/${path}`, {
    credentials: 'include',
    ...options,
  })
  if (resp.status === 401) {
    const { useAuthStore } = await import('../stores/auth')
    useAuthStore().logout()
    throw new Error('Unauthorized')
  }
  return resp
}
