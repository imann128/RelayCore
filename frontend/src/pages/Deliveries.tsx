import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { deliveriesApi, Delivery } from '@/api/deliveries'
import { sourcesApi } from '@/api/sources'
import { Card } from '@/components/ui/Card'
import { Select } from '@/components/ui/Select'
import { Button } from '@/components/ui/Button'
import { StatusBadge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { Icon } from '@/components/ui/Icon'
import Modal from '@/components/Modal'
import PageHeader from '@/components/PageHeader'
import { fmtDate, fmtRelative } from '@/lib/utils'

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'received',      label: 'Received' },
  { value: 'delivered',     label: 'Delivered' },
  { value: 'retrying',      label: 'Retrying' },
  { value: 'dead_lettered', label: 'Dead Lettered' },
  { value: 'duplicate',     label: 'Duplicate' },
  { value: 'sig_failed',    label: 'Sig Failed' },
]

export default function Deliveries() {
  const [status, setStatus] = useState('')
  const [sourceId, setSourceId] = useState<number | undefined>()
  const [page, setPage] = useState(1)
  const [detail, setDetail] = useState<Delivery | null>(null)

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['deliveries', { status, sourceId, page }],
    queryFn: () => deliveriesApi.list({ status: status || undefined, source: sourceId, page }),
    refetchInterval: 10_000,
  })
  const { data: sources } = useQuery({ queryKey: ['sources'], queryFn: sourcesApi.list })
  const totalPages = data ? Math.ceil(data.count / 50) : 1

  return (
    <div className="p-8">
      <PageHeader
        title="Deliveries"
        description="Immutable log of every inbound webhook event. Click a row for full detail."
        action={
          <Button variant="secondary" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <Icon name="refresh" size={15} className={isFetching ? 'animate-spin' : ''} /> Refresh
          </Button>
        }
      />

      <div className="flex gap-3 mb-5">
        <Select className="w-44" value={status} onChange={e => { setStatus(e.target.value); setPage(1) }}>
          {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </Select>
        <Select className="w-52" value={sourceId ?? ''} onChange={e => { setSourceId(e.target.value ? parseInt(e.target.value) : undefined); setPage(1) }}>
          <option value="">All sources</option>
          {sources?.results.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </Select>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size={24} /></div>
      ) : (
        <Card className="p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-[#1e3d24]">
              <tr>
                {['ID', 'Source', 'Event', 'Key', 'Status', 'Attempts', 'Received'].map(h => (
                  <th key={h} className="text-left px-5 py-3 text-xs font-medium text-green-500/60 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data?.results.map(d => (
                <tr
                  key={d.id}
                  className="border-b border-[#1e3d24]/50 hover:bg-[#183d21]/40 transition-colors cursor-pointer"
                  onClick={() => setDetail(d)}
                >
                  <td className="px-5 py-3.5 font-mono text-xs text-green-400/50">#{d.id}</td>
                  <td className="px-5 py-3.5 text-green-100">{d.source_name || '—'}</td>
                  <td className="px-5 py-3.5 font-mono text-xs text-green-300/70">{d.event_type || '—'}</td>
                  <td className="px-5 py-3.5 font-mono text-xs text-green-400/40 max-w-xs truncate">{d.idempotency_key}</td>
                  <td className="px-5 py-3.5"><StatusBadge status={d.status} /></td>
                  <td className="px-5 py-3.5 text-green-300/70 text-center">{d.attempt_count}</td>
                  <td className="px-5 py-3.5 text-green-400/50 text-xs">{fmtRelative(d.received_at)}</td>
                </tr>
              ))}
              {!data?.results.length && (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-green-600/50">
                    No deliveries match your filters.
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
        <Modal title={`Delivery #${detail.id}`} open onClose={() => setDetail(null)} width="max-w-2xl">
          <div className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-green-500/60 mb-1">Status</p>
                <StatusBadge status={detail.status} />
              </div>
              <div>
                <p className="text-xs text-green-500/60 mb-1">Attempts</p>
                <p className="text-green-100">{detail.attempt_count}</p>
              </div>
              <div>
                <p className="text-xs text-green-500/60 mb-1">Received</p>
                <p className="text-green-100">{fmtDate(detail.received_at)}</p>
              </div>
              <div>
                <p className="text-xs text-green-500/60 mb-1">Delivered</p>
                <p className="text-green-100">{fmtDate(detail.delivered_at)}</p>
              </div>
            </div>

            <div>
              <p className="text-xs text-green-500/60 mb-1">Idempotency Key</p>
              <p className="font-mono text-xs text-green-300/70 bg-[#183d21] rounded px-3 py-2 break-all">
                {detail.idempotency_key}
              </p>
            </div>

            {detail.last_error && (
              <div>
                <p className="text-xs text-red-400 mb-1">Last Error</p>
                <p className="font-mono text-xs text-red-300 bg-red-950/30 border border-red-900/50 rounded px-3 py-2 whitespace-pre-wrap">
                  {detail.last_error}
                </p>
              </div>
            )}

            <div>
              <p className="text-xs text-green-500/60 mb-1">Raw Payload</p>
              <pre className="font-mono text-xs text-green-200/80 bg-[#183d21] rounded px-3 py-3 overflow-auto max-h-64">
                {JSON.stringify(detail.raw_payload, null, 2)}
              </pre>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
