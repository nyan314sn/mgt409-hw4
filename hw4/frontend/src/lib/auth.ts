import { createContext, useContext } from 'react'
import type { RegisterInput, User } from './authApi.ts'

export type AuthContextValue = {
  /** undefined while the session check is in flight, null when logged out. */
  user: User | null | undefined
  login: (email: string, password: string) => Promise<User>
  register: (input: RegisterInput) => Promise<User>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
