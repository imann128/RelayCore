import client from './client'

export interface AuditEntry {
  id: number
  actor: string
  action: string
  resource_type: string
  resource_repr: string
  object_id: string
  changes: Record<string, [string, string]>
  timestamp: string
}

export interface PaginatedAuditLog {
  count: number
  results: AuditEntry[]
}

export const auditLogApi = {
  list: (page = 1): Promise<PaginatedAuditLog> =>
    client.get<PaginatedAuditLog>('/audit-log/', { params: { page } }).then(r => r.data),
}
