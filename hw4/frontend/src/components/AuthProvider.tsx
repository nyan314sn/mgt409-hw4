import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { AuthContext } from '../lib/auth.ts'
import { ApiError, authApi, type RegisterInput, type User } from '../lib/authApi.ts'

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null | undefined>(undefined)

  useEffect(() => {
    let active = true
    let timer: number | undefined
    // Only a 401 means "logged out". If the server is unreachable, show the shopper as
    // logged out for now but keep checking, so the session comes back when the server does.
    const check = () => {
      authApi.me()
        .then((u) => active && setUser(u))
        .catch((err) => {
          if (!active) return
          if (err instanceof ApiError && err.status === 401) {
            setUser(null)
          } else {
            setUser((current) => current ?? null)
            timer = window.setTimeout(check, 5000)
          }
        })
    }
    check()
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const u = await authApi.login(email, password)
    setUser(u)
    return u
  }, [])

  const register = useCallback(async (input: RegisterInput) => {
    const u = await authApi.register(input)
    setUser(u)
    return u
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      setUser(null)
    }
  }, [])

  const value = useMemo(() => ({ user, login, register, logout }), [user, login, register, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
