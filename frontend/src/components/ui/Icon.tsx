interface Props {
  name: string
  size?: number
  className?: string
}

export function Icon({ name, size = 20, className = '' }: Props) {
  return (
    <span
      className={`material-icons-round select-none leading-none ${className}`}
      style={{ fontSize: size }}
    >
      {name}
    </span>
  )
}
