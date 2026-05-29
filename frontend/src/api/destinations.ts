import client from './client'

export interface Destination {
  id: number
  name: string
  url: string
  timeout_seconds: number
  is_active: boolean
  created_at: string
}

export type CreateDestination = Omit<Destination, 'id' | 'created_at'> & { auth_header?: string }

export const destinationsApi = {
  list: () => client.get<{ results: Destination[]; count: number }>('/destinations/').then(r => r.data),
  create: (data: CreateDestination) => client.post<Destination>('/destinations/', data).then(r => r.data),
  update: (id: number, data: Partial<CreateDestination>) => client.patch<Destination>(`/destinations/${id}/`, data).then(r => r.data),
  delete: (id: number) => client.delete(`/destinations/${id}/`),
  toggleActive: (id: number) => client.post<Destination>(`/destinations/${id}/toggle-active/`).then(r => r.data),
}
