import client from './client'

export type DeliveryStatus =
  | 'received' | 'duplicate' | 'sig_failed'
  | 'routed' | 'delivered' | 'retrying' | 'dead_lettered'

export interface Delivery {
  id: number
  source: number | null
  source_name: string
  idempotency_key: string
  event_type: string
  raw_payload: Record<string, unknown>
  headers: Record<string, string>
  status: DeliveryStatus
  attempt_count: number
  last_error: string
  received_at: string
  delivered_at: string | null
}

export const deliveriesApi = {
  list: (params?: { status?: string; source?: number; page?: number }) =>
    client.get<{ results: Delivery[]; count: number; next: string | null; previous: string | null }>(
      '/deliveries/', { params }
    ).then(r => r.data),
  get: (id: number) => client.get<Delivery>(`/deliveries/${id}/`).then(r => r.data),
}
