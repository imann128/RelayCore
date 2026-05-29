import { cn } from '@/lib/utils'
import { InputHTMLAttributes, forwardRef } from 'react'

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        'w-full rounded-md bg-[#183d21] border border-[#245c2e] text-slate-100 px-3 py-2 text-sm placeholder:text-slate-500',
        'focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent disabled:opacity-50',
        className,
      )}
      {...props}
    />
  )
)
Input.displayName = 'Input'
