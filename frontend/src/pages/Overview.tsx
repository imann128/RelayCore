import { useQuery } from '@tanstack/react-query'
import { metricsApi } from '@/api/metrics'
import { deliveriesApi } from '@/api/deliveries'
import { sourcesApi } from '@/api/sources'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { Icon } from '@/components/ui/Icon'
import { fmtRelative } from '@/lib/utils'

function MetricCard({ label, value, icon, accent = false }: {
  label: string; value: string | number; icon: string; accent?: boolean
}) {
  return (
    <Card className="flex items-center gap-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${accent ? 'bg-green-600/20' : 'bg-[#183d21]'}`}>
        <Icon name={icon} size={20} className={accent ? 'text-green-400' : 'text-slate-400'} />
      </div>
      <div>
        <p className="text-xs text-slate-500 font-light">{label}</p>
        <p className="text-xl font-semibold text-slate-100 mt-0.5">{value}</p>
      </div>
    </Card>
  )
}

export default function Overview() {
  const { data: metrics, isLoading: ml } = useQuery({
    queryKey: ['metrics'],
    queryFn: metricsApi.get,
    refetchInterval: 10_000,
  })
  const { data: deliveries, isLoading: dl } = useQuery({
    queryKey: ['deliveries', 'recent'],
    queryFn: () => deliveriesApi.list({ page: 1 }),
    refetchInterval: 10_000,
  })
  const { data: sources } = useQuery({ queryKey: ['sources'], queryFn: sourcesApi.list })

  const l = metrics?.latest ?? {}
  const successRate = l['webhook.success_rate'] ?? l['success_rate']
  const queueDepth  = l['webhook.queue_depth']  ?? l['queue_depth']
  const dlq         = l['webhook.dead_letter_count'] ?? l['dead_letter_count']
  const throughput  = l['webhook.throughput_1m'] ?? l['throughput_1m']
  const duplicates  = l['webhook.duplicate_count']
  const sigFailed   = l['webhook.sig_failed_count']

  const activeSources = sources?.results.filter(s => s.is_active) ?? []

  return (
    <div className="p-8">

      {/* ── Hero ── */}
      <div className="relative overflow-hidden rounded-2xl mb-8
        bg-gradient-to-br from-[#0f2916] via-[#0f2314] to-[#091a0d]
        border border-[#245c2e]">
        {/* Decorative background grid */}
        <div className="absolute inset-0 opacity-10"
          style={{ backgroundImage: 'radial-gradient(#22c55e 1px, transparent 1px)', backgroundSize: '24px 24px' }} />

        <div className="relative px-8 py-10">
          <div className="flex items-start justify-between flex-wrap gap-6">
            <div>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-green-600 flex items-center justify-center shadow-lg shadow-green-900/50">
                  <Icon name="bolt" size={22} className="text-white" />
                </div>
                <span className="text-xs font-medium text-green-400 bg-green-900/30 border border-green-800 px-2.5 py-1 rounded-full">
                  Live
                </span>
              </div>
              <h1 className="text-3xl font-bold text-slate-100 mb-2">Webhook Relay</h1>
              <p className="text-green-300/60 text-sm max-w-lg leading-relaxed">
                Universal event gateway — accepts events from any HTTP source, verifies authenticity,
                deduplicates atomically, routes by configurable rules, transforms payloads, and
                delivers with exponential backoff retries.
              </p>
            </div>

            {/* Quick stat pills */}
            <div className="flex flex-col gap-2 text-sm">
              <div className="flex items-center gap-2 bg-[#183d21] border border-[#1e3d24] rounded-lg px-4 py-2.5">
                <Icon name="sensors" size={16} className="text-green-400" />
                <span className="text-slate-300">{activeSources.length} active source{activeSources.length !== 1 ? 's' : ''}</span>
              </div>
              <div className="flex items-center gap-2 bg-[#183d21] border border-[#1e3d24] rounded-lg px-4 py-2.5">
                <Icon name="inventory_2" size={16} className="text-slate-400" />
                <span className="text-slate-300">{deliveries?.count ?? 0} total deliveries</span>
              </div>
              <div className="flex items-center gap-2 bg-[#183d21] border border-[#1e3d24] rounded-lg px-4 py-2.5">
                <Icon name="schedule" size={16} className="text-slate-400" />
                <span className="text-slate-300">Refreshes every 10s</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Metric cards ── */}
      <div className="grid grid-cols-2 gap-4 mb-6 lg:grid-cols-3 xl:grid-cols-6">
        <MetricCard icon="check_circle" label="Success Rate" accent
          value={successRate != null ? `${(successRate * 100).toFixed(1)}%` : '—'} />
        <MetricCard icon="pending" label="Queue Depth"
          value={queueDepth ?? '—'} />
        <MetricCard icon="warning" label="Dead Letters"
          value={dlq ?? '—'} />
        <MetricCard icon="speed" label="Throughput / min"
          value={throughput != null ? throughput.toFixed(1) : '—'} />
        <MetricCard icon="content_copy" label="Duplicates Dropped"
          value={duplicates ?? '—'} />
        <MetricCard icon="gpp_bad" label="Sig Failures"
          value={sigFailed ?? '—'} />
      </div>

      {/* ── Recent deliveries ── */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-100">Recent Deliveries</h2>
          {(ml || dl) && <Spinner size={16} />}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1e3d24]">
                {['ID', 'Source', 'Event', 'Status', 'Received'].map(h => (
                  <th key={h} className="text-left py-2 pr-4 text-xs font-medium text-slate-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {deliveries?.results.slice(0, 10).map(d => (
                <tr key={d.id} className="border-b border-[#1e3d24]/50 hover:bg-[#183d21]/30 transition-colors">
                  <td className="py-2.5 pr-4 font-mono text-xs text-slate-500">#{d.id}</td>
                  <td className="py-2.5 pr-4 text-slate-300">{d.source_name || '—'}</td>
                  <td className="py-2.5 pr-4 font-mono text-xs text-slate-400">{d.event_type || '—'}</td>
                  <td className="py-2.5 pr-4"><StatusBadge status={d.status} /></td>
                  <td className="py-2.5 text-slate-500 text-xs">{fmtRelative(d.received_at)}</td>
                </tr>
              ))}
              {!deliveries?.results.length && !dl && (
                <tr><td colSpan={5} className="py-10 text-center text-slate-600 text-sm">
                  No deliveries yet — send a webhook to get started.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* ── Active sources ── */}
      {activeSources.length > 0 && (
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {activeSources.map(s => (
            <Card key={s.id} className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-100">{s.name}</p>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">/webhooks/receive/{s.slug}/</p>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
