import client from './client'

export interface Source {
  id: number
  name: string
  slug: string
  signature_scheme: 'github_hmac' | 'none'
  rate_limit_per_minute: number
  is_active: boolean
  created_at: string
}

export type CreateSource = Omit<Source, 'id' | 'created_at'> & { secret?: string }

export const sourcesApi = {
  list: () => client.get<{ results: Source[]; count: number }>('/sources/').then(r => r.data),
  create: (data: CreateSource) => client.post<Source>('/sources/', data).then(r => r.data),
  update: (id: number, data: Partial<CreateSource>) => client.patch<Source>(`/sources/${id}/`, data).then(r => r.data),
  delete: (id: number) => client.delete(`/sources/${id}/`),
  toggleActive: (id: number) => client.post<Source>(`/sources/${id}/toggle-active/`).then(r => r.data),
}
