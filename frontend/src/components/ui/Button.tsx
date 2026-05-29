import { cn } from '@/lib/utils'
import { ButtonHTMLAttributes, forwardRef } from 'react'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md'
}

const base = 'inline-flex items-center justify-center gap-1.5 rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed'

const variants = {
  primary:   'bg-green-600 hover:bg-green-500 text-white',
  secondary: 'bg-[#183d21] hover:bg-[#1e4f29] text-slate-100 border border-[#245c2e]',
  danger:    'bg-red-700 hover:bg-red-600 text-white',
  ghost:     'hover:bg-[#183d21] text-slate-300',
}

const sizes = {
  sm: 'text-xs px-2.5 py-1.5',
  md: 'text-sm px-4 py-2',
}

export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => (
    <button ref={ref} className={cn(base, variants[variant], sizes[size], className)} {...props} />
  )
)
Button.displayName = 'Button'
