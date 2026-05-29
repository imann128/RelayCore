import { ReactNode, useEffect } from 'react'
import { Icon } from '@/components/ui/Icon'
import { cn } from '@/lib/utils'

interface Props {
  title: string
  open: boolean
  onClose: () => void
  children: ReactNode
  width?: string
}

export default function Modal({ title, open, onClose, children, width = 'max-w-lg' }: Props) {
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className={cn('relative w-full mx-4 rounded-xl bg-[#0f2314] border border-[#245c2e] shadow-2xl', width)}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1e3d24]">
          <h2 className="text-sm font-semibold text-slate-100">{title}</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">
            <Icon name="close" size={18} />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}
