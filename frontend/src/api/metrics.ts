import client from './client'

export interface MetricPoint {
  id: number
  name: string
  value: number
  labels: Record<string, string>
  timestamp: string
}

export interface MetricsResponse {
  latest: Record<string, number>
  history: MetricPoint[]
}

export const metricsApi = {
  get: () => client.get<MetricsResponse>('/metrics/').then(r => r.data),
}
