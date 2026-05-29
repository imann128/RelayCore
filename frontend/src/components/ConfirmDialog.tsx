import Modal from './Modal'
import { Button } from '@/components/ui/Button'

interface Props {
  open: boolean
  title?: string
  message: string
  onConfirm: () => void
  onCancel: () => void
  loading?: boolean
}

export default function ConfirmDialog({ open, title = 'Confirm', message, onConfirm, onCancel, loading }: Props) {
  return (
    <Modal title={title} open={open} onClose={onCancel} width="max-w-sm">
      <p className="text-sm text-slate-300 mb-6">{message}</p>
      <div className="flex justify-end gap-3">
        <Button variant="secondary" onClick={onCancel} disabled={loading}>Cancel</Button>
        <Button variant="danger" onClick={onConfirm} disabled={loading}>
          {loading ? 'Deleting…' : 'Delete'}
        </Button>
      </div>
    </Modal>
  )
}
