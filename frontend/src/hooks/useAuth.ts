import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { authApi, User } from '@/api/auth'

export function useAuth() {
  const qc = useQueryClient()

  const { data: user, isLoading } = useQuery<User | null>({
    queryKey: ['me'],
    queryFn: async () => {
      try { return await authApi.me() }
      catch { return null }
    },
    staleTime: Infinity,
    retry: false,
  })

  const loginMut = useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      authApi.login(username, password),
    onSuccess: (data) => qc.setQueryData(['me'], data),
  })

  const logoutMut = useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => qc.setQueryData(['me'], null),
  })

  return {
    user: user ?? null,
    isLoading,
    isAuthenticated: !!user,
    login: loginMut.mutateAsync,
    loginError: loginMut.error,
    logout: logoutMut.mutate,
  }
}
