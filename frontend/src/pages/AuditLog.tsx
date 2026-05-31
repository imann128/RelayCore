import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { auditLogApi, AuditEntry } from '@/api/auditlog'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { Icon } from '@/components/ui/Icon'
import Modal from '@/components/Modal'
import PageHeader from '@/components/PageHeader'
import { fmtDate, fmtRelative } from '@/lib/utils'

const ACTION_COLORS: Record<string, string> = {
  Create: 'text-green-400 bg-green-900/30 border-green-800',
  Update: 'text-blue-400 bg-blue-900/30 border-blue-800',
  Delete: 'text-red-400 bg-red-900/30 border-red-800',
}

function ActionBadge({ action }: { action: string }) {
  const cls = ACTION_COLORS[action] ?? 'text-green-400/50 bg-[#183d21] border-[#245c2e]'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium border ${cls}`}>
      {action}
    </span>
  )
}

function ChangesTable({ changes }: { changes: Record<string, [string, string]> }) {
  const entries = Object.entries(changes)
  if (!entries.length) return <p className="text-green-400/50 text-xs">No field changes recorded.</p>
  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="border-b border-[#1e3d24]">
          <th className="text-left py-1.5 pr-4 text-green-500/60 font-medium uppercase tracking-wide">Field</th>
          <th className="text-left py-1.5 pr-4 text-green-500/60 font-medium uppercase tracking-wide">From</th>
          <th className="text-left py-1.5 text-green-500/60 font-medium uppercase tracking-wide">To</th>
        </tr>
      </thead>
      <tbody>
        {entries.map(([field, [from, to]]) => (
          <tr key={field} className="border-b border-[#1e3d24]/50">
            <td className="py-1.5 pr-4 font-mono text-green-300/70">{field}</td>
            <td className="py-1.5 pr-4 font-mono text-red-400/70">{from || '—'}</td>
            <td className="py-1.5 font-mono text-green-400/70">{to || '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default function AuditLog() {
  const [page, setPage] = useState(1)
  const [detail, setDetail] = useState<AuditEntry | null>(null)

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['audit-log', page],
    queryFn: () => auditLogApi.list(page),
    refetchInterval: 30_000,
  })

  const totalPages = data ? Math.ceil(data.count / 50) : 1

  return (
    <div className="p-8">
      <PageHeader
        title="Audit Log"
        description="Immutable record of every create, update, and delete action on sources, destinations, and routes."
        action={
          <Button variant="secondary" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <Icon name="refresh" size={15} className={isFetching ? 'animate-spin' : ''} /> Refresh
          </Button>
        }
      />

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size={24} /></div>
      ) : (
        <Card className="p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-[#1e3d24]">
              <tr>
                {['Time', 'Actor', 'Action', 'Resource', 'Object'].map(h => (
                  <th key={h} className="text-left px-5 py-3 text-xs font-medium text-green-500/60 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data?.results.map(entry => (
                <tr
                  key={entry.id}
                  className="border-b border-[#1e3d24]/50 hover:bg-[#183d21]/40 transition-colors cursor-pointer"
                  onClick={() => setDetail(entry)}
                >
                  <td className="px-5 py-3.5 text-green-400/50 text-xs">{fmtRelative(entry.timestamp)}</td>
                  <td className="px-5 py-3.5 text-green-100 font-mono text-xs">{entry.actor}</td>
                  <td className="px-5 py-3.5"><ActionBadge action={entry.action} /></td>
                  <td className="px-5 py-3.5 text-green-300/70 capitalize">{entry.resource_type}</td>
                  <td className="px-5 py-3.5 text-green-100 truncate max-w-xs">{entry.resource_repr}</td>
                </tr>
              ))}
              {!data?.results.length && (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-green-600/50">
                    No audit entries yet — create, edit, or delete a source, destination, or route to see entries here.
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-[#1e3d24]">
              <span className="text-xs text-green-400/50">{data?.count} total</span>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
                  <Icon name="chevron_left" size={16} />
                </Button>
                <span className="text-xs text-green-300/70">{page} / {totalPages}</span>
                <Button variant="ghost" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
                  <Icon name="chevron_right" size={16} />
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}

      {detail && (
        <Modal title="Audit Entry" open onClose={() => setDetail(null)} width="max-w-2xl">
          <div className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-green-500/60 mb-1">Actor</p>
                <p className="text-green-100 font-mono">{detail.actor}</p>
              </div>
              <div>
                <p className="text-xs text-green-500/60 mb-1">Action</p>
                <ActionBadge action={detail.action} />
              </div>
              <div>
                <p className="text-xs text-green-500/60 mb-1">Resource</p>
                <p className="text-green-100 capitalize">{detail.resource_type} #{detail.object_id}</p>
              </div>
              <div>
                <p className="text-xs text-green-500/60 mb-1">Timestamp</p>
                <p className="text-green-100">{fmtDate(detail.timestamp)}</p>
              </div>
            </div>
            <div>
              <p className="text-xs text-green-500/60 mb-2">Field Changes</p>
              <div className="bg-[#183d21] rounded px-3 py-2">
                <ChangesTable changes={detail.changes} />
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
