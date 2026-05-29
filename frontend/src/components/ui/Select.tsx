import { cn } from '@/lib/utils'
import { SelectHTMLAttributes, forwardRef } from 'react'

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        'w-full rounded-md bg-[#183d21] border border-[#245c2e] text-slate-100 px-3 py-2 text-sm',
        'focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent disabled:opacity-50',
        className,
      )}
      {...props}
    >
      {children}
    </select>
  )
)
Select.displayName = 'Select'
