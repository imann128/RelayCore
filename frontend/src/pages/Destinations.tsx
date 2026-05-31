import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { destinationsApi, Destination, CreateDestination } from '@/api/destinations'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { Icon } from '@/components/ui/Icon'
import Modal from '@/components/Modal'
import ConfirmDialog from '@/components/ConfirmDialog'
import PageHeader from '@/components/PageHeader'

const empty: CreateDestination = { name: '', url: '', timeout_seconds: 30, is_active: true, auth_header: '' }

export default function Destinations() {
  const qc = useQueryClient()
  const [modal, setModal] = useState<'create' | 'edit' | null>(null)
  const [editing, setEditing] = useState<Destination | null>(null)
  const [form, setForm] = useState<CreateDestination>(empty)
  const [deleteId, setDeleteId] = useState<number | null>(null)
  const [formError, setFormError] = useState<string>('')

  const { data, isLoading } = useQuery({ queryKey: ['destinations'], queryFn: destinationsApi.list })
  const inv = () => qc.invalidateQueries({ queryKey: ['destinations'] })

  function extractError(err: any): string {
    const d = err?.response?.data
    if (!d) return 'An unexpected error occurred.'
    if (d.url) return Array.isArray(d.url) ? d.url[0] : d.url
    if (d.detail) return d.detail
    const first = Object.values(d)[0]
    return Array.isArray(first) ? (first as string[])[0] : String(first)
  }

  const createMut = useMutation({
    mutationFn: destinationsApi.create,
    onSuccess: () => { inv(); setModal(null); setFormError('') },
    onError: (err: any) => setFormError(extractError(err)),
  })
  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<CreateDestination> }) => destinationsApi.update(id, data),
    onSuccess: () => { inv(); setModal(null); setFormError('') },
    onError: (err: any) => setFormError(extractError(err)),
  })
  const deleteMut = useMutation({ mutationFn: destinationsApi.delete, onSuccess: () => { inv(); setDeleteId(null) } })
  const toggleMut = useMutation({ mutationFn: destinationsApi.toggleActive, onSuccess: inv })

  function openCreate() { setForm(empty); setFormError(''); setModal('create') }
  function openEdit(d: Destination) { setEditing(d); setForm({ ...d, auth_header: '' }); setFormError(''); setModal('edit') }
  function save() {
    if (modal === 'create') createMut.mutate(form)
    else if (editing) updateMut.mutate({ id: editing.id, data: form })
  }
  const saving = createMut.isPending || updateMut.isPending

  return (
    <div className="p-8">
      <PageHeader title="Destinations" description="Registered webhook consumers. Payloads are delivered here after transformation."
        action={<Button onClick={openCreate}><Icon name="add" size={16} />New Destination</Button>} />

      {isLoading ? <div className="flex justify-center py-16"><Spinner size={24} /></div> : (
        <Card className="p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-[#1e3d24]">
              <tr>{['Name', 'URL', 'Timeout', 'Status', ''].map(h =>
                <th key={h} className="text-left px-5 py-3 text-xs font-medium text-slate-500">{h}</th>)}</tr>
            </thead>
            <tbody>
              {data?.results.map(d => (
                <tr key={d.id} className="border-b border-[#1e3d24]/50 hover:bg-[#183d21]/20 transition-colors">
                  <td className="px-5 py-3.5 font-medium text-slate-100">{d.name}</td>
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-400 max-w-xs truncate">{d.url}</td>
                  <td className="px-5 py-3.5 text-slate-400">{d.timeout_seconds}s</td>
                  <td className="px-5 py-3.5">
                    <Badge label={d.is_active ? 'active' : 'inactive'} color={d.is_active ? 'green' : 'gray'} />
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-3 justify-end">
                      <button onClick={() => toggleMut.mutate(d.id)} className="text-slate-500 hover:text-green-400 transition-colors">
                        <Icon name="power_settings_new" size={17} /></button>
                      <button onClick={() => openEdit(d)} className="text-slate-500 hover:text-blue-400 transition-colors">
                        <Icon name="edit" size={17} /></button>
                      <button onClick={() => setDeleteId(d.id)} className="text-slate-500 hover:text-red-400 transition-colors">
                        <Icon name="delete" size={17} /></button>
                    </div>
                  </td>
                </tr>
              ))}
              {!data?.results.length && (
                <tr><td colSpan={5} className="px-5 py-12 text-center text-slate-600">No destinations yet.</td></tr>
              )}
            </tbody>
          </table>
        </Card>
      )}

      <Modal title={modal === 'create' ? 'New Destination' : 'Edit Destination'} open={modal !== null} onClose={() => setModal(null)}>
        <div className="space-y-4">
          <div><Label>Name</Label><Input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} placeholder="Slack Engineering" /></div>
          <div><Label>URL</Label><Input value={form.url} onChange={e => setForm(p => ({ ...p, url: e.target.value }))} placeholder="https://hooks.slack.com/..." /></div>
          <div><Label>Auth Header {modal === 'edit' && <span className="text-slate-600">(blank = keep current)</span>}</Label>
            <Input type="password" value={form.auth_header ?? ''} onChange={e => setForm(p => ({ ...p, auth_header: e.target.value }))} placeholder="Bearer token — stored encrypted" /></div>
          <div><Label>Timeout (seconds)</Label>
            <Input type="number" value={form.timeout_seconds} onChange={e => setForm(p => ({ ...p, timeout_seconds: parseInt(e.target.value) }))} /></div>
          <div className="flex items-center gap-2">
            <input id="dst_active" type="checkbox" checked={form.is_active}
              onChange={e => setForm(p => ({ ...p, is_active: e.target.checked }))}
              className="rounded border-[#245c2e] bg-[#183d21] text-green-600" />
            <Label htmlFor="dst_active" className="mb-0">Active</Label>
          </div>
          {formError && (
            <div className="flex items-center gap-2 text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-md px-3 py-2">
              <Icon name="error_outline" size={16} />{formError}
            </div>
          )}
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={() => setModal(null)}>Cancel</Button>
          <Button onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save'}</Button>
        </div>
      </Modal>

      <ConfirmDialog open={deleteId !== null} message="Delete this destination? Routes pointing to it will also be deleted."
        onConfirm={() => deleteId && deleteMut.mutate(deleteId)} onCancel={() => setDeleteId(null)} loading={deleteMut.isPending} />
    </div>
  )
}
