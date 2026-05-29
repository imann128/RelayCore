import client from './client'

export interface User {
  id: number
  username: string
  email: string
  is_staff: boolean
}

export const authApi = {
  me: () => client.get<User>('/auth/me/').then(r => r.data),
  login: (username: string, password: string) =>
    client.post<User>('/auth/login/', { username, password }).then(r => r.data),
  logout: () => client.post('/auth/logout/').then(r => r.data),
}
