import { cn } from '@/lib/utils'
import { HTMLAttributes } from 'react'

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('rounded-xl bg-[#0f2314] border border-[#1e3d24] p-6', className)} {...props} />
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn('text-base font-semibold text-slate-100', className)} {...props} />
}
