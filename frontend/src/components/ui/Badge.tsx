import { cn } from '@/lib/utils'

const variants: Record<string, string> = {
  green:  'bg-green-900/40 text-green-400 border border-green-800',
  red:    'bg-red-900/40    text-red-400    border border-red-800',
  yellow: 'bg-yellow-900/40 text-yellow-400 border border-yellow-800',
  gray:   'bg-[#183d21]     text-slate-400  border border-[#245c2e]',
  blue:   'bg-blue-900/40   text-blue-400   border border-blue-800',
}

export function Badge({ label, color = 'gray' }: { label: string; color?: keyof typeof variants }) {
  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium', variants[color])}>
      {label}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; color: string }> = {
    received:      { label: 'received',    color: 'blue'   },
    duplicate:     { label: 'duplicate',   color: 'yellow' },
    sig_failed:    { label: 'sig failed',  color: 'red'    },
    routed:        { label: 'routed',      color: 'blue'   },
    delivered:     { label: 'delivered',   color: 'green'  },
    retrying:      { label: 'retrying',    color: 'yellow' },
    dead_lettered: { label: 'dead letter', color: 'red'    },
  }
  const { label, color } = map[status] ?? { label: status, color: 'gray' }
  return <Badge label={label} color={color as any} />
}
