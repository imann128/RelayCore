import client from './client'

export interface Route {
  id: number
  source: number
  source_name: string
  event_type: string
  condition: Record<string, string>
  destination: number
  destination_name: string
  transformer_class: string
  transformer_class_display: string
  priority: number
  is_active: boolean
  rate_limit_per_minute: number | null
}

export type CreateRoute = {
  source: number
  event_type?: string
  condition?: Record<string, string>
  destination: number
  transformer_class: string
  priority?: number
  is_active?: boolean
  rate_limit_per_minute?: number | null
}

export const TRANSFORMER_CHOICES = [
  { value: 'github_to_slack',   label: 'GitHub → Slack' },
  { value: 'github_to_discord', label: 'GitHub → Discord' },
  { value: 'calendar_to_db',    label: 'Google Calendar → Database' },
  { value: 'form_to_email',     label: 'HTML Form → Email' },
]

export const routesApi = {
  list: (sourceId?: number) => {
    const params = sourceId ? { source: sourceId } : {}
    return client.get<{ results: Route[]; count: number }>('/routes/', { params }).then(r => r.data)
  },
  create: (data: CreateRoute) => client.post<Route>('/routes/', data).then(r => r.data),
  update: (id: number, data: Partial<CreateRoute>) => client.patch<Route>(`/routes/${id}/`, data).then(r => r.data),
  delete: (id: number) => client.delete(`/routes/${id}/`),
  toggleActive: (id: number) => client.post<Route>(`/routes/${id}/toggle-active/`).then(r => r.data),
}
