import { cn } from '@/lib/utils'
import { LabelHTMLAttributes } from 'react'

export function Label({ className, ...props }: LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn('block text-xs font-medium text-slate-400 mb-1', className)} {...props} />
}
