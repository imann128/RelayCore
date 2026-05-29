import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sourcesApi, Source, CreateSource } from '@/api/sources'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { Icon } from '@/components/ui/Icon'
import Modal from '@/components/Modal'
import ConfirmDialog from '@/components/ConfirmDialog'
import PageHeader from '@/components/PageHeader'

const empty: CreateSource = { name: '', slug: '', signature_scheme: 'none', rate_limit_per_minute: 100, is_active: true, secret: '' }

export default function Sources() {
  const qc = useQueryClient()
  const [modal, setModal] = useState<'create' | 'edit' | null>(null)
  const [editing, setEditing] = useState<Source | null>(null)
  const [form, setForm] = useState<CreateSource>(empty)
  const [deleteId, setDeleteId] = useState<number | null>(null)

  const { data, isLoading } = useQuery({ queryKey: ['sources'], queryFn: sourcesApi.list })
  const inv = () => qc.invalidateQueries({ queryKey: ['sources'] })

  const createMut = useMutation({ mutationFn: sourcesApi.create, onSuccess: () => { inv(); setModal(null) } })
  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<CreateSource> }) => sourcesApi.update(id, data),
    onSuccess: () => { inv(); setModal(null) },
  })
  const deleteMut = useMutation({ mutationFn: sourcesApi.delete, onSuccess: () => { inv(); setDeleteId(null) } })
  const toggleMut = useMutation({ mutationFn: sourcesApi.toggleActive, onSuccess: inv })

  function openCreate() { setForm(empty); setModal('create') }
  function openEdit(s: Source) { setEditing(s); setForm({ ...s, secret: '' }); setModal('edit') }
  function save() {
    if (modal === 'create') createMut.mutate(form)
    else if (editing) updateMut.mutate({ id: editing.id, data: form })
  }
  const saving = createMut.isPending || updateMut.isPending

  return (
    <div className="p-8">
      <PageHeader title="Sources" description="Registered webhook producers. Each gets a unique ingestion URL."
        action={<Button onClick={openCreate}><Icon name="add" size={16} />New Source</Button>} />

      {isLoading ? <div className="flex justify-center py-16"><Spinner size={24} /></div> : (
        <Card className="p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-[#1e3d24]">
              <tr>{['Name', 'Slug / URL', 'Auth Scheme', 'Rate Limit', 'Status', ''].map(h =>
                <th key={h} className="text-left px-5 py-3 text-xs font-medium text-slate-500">{h}</th>)}</tr>
            </thead>
            <tbody>
              {data?.results.map(s => (
                <tr key={s.id} className="border-b border-[#1e3d24]/50 hover:bg-[#183d21]/20 transition-colors">
                  <td className="px-5 py-3.5 font-medium text-slate-100">{s.name}</td>
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-400">/webhooks/receive/{s.slug}/</td>
                  <td className="px-5 py-3.5">
                    <Badge label={s.signature_scheme} color={s.signature_scheme === 'github_hmac' ? 'blue' : 'gray'} />
                  </td>
                  <td className="px-5 py-3.5 text-slate-400">{s.rate_limit_per_minute}/min</td>
                  <td className="px-5 py-3.5">
                    <Badge label={s.is_active ? 'active' : 'inactive'} color={s.is_active ? 'green' : 'gray'} />
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-3 justify-end">
                      <button onClick={() => toggleMut.mutate(s.id)} title={s.is_active ? 'Deactivate' : 'Activate'}
                        className="text-slate-500 hover:text-green-400 transition-colors">
                        <Icon name="power_settings_new" size={17} />
                      </button>
                      <button onClick={() => openEdit(s)} className="text-slate-500 hover:text-blue-400 transition-colors">
                        <Icon name="edit" size={17} />
                      </button>
                      <button onClick={() => setDeleteId(s.id)} className="text-slate-500 hover:text-red-400 transition-colors">
                        <Icon name="delete" size={17} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!data?.results.length && (
                <tr><td colSpan={6} className="px-5 py-12 text-center text-slate-600">No sources yet.</td></tr>
              )}
            </tbody>
          </table>
        </Card>
      )}

      <Modal title={modal === 'create' ? 'New Source' : 'Edit Source'} open={modal !== null} onClose={() => setModal(null)}>
        <div className="space-y-4">
          <div><Label>Name</Label><Input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} placeholder="GitHub Production" /></div>
          <div><Label>Slug</Label><Input value={form.slug} onChange={e => setForm(p => ({ ...p, slug: e.target.value }))} placeholder="github-prod" />
            <p className="text-xs text-slate-500 mt-1">Lowercase, hyphens only. Used in the ingestion URL.</p></div>
          <div><Label>Signature Scheme</Label>
            <Select value={form.signature_scheme} onChange={e => setForm(p => ({ ...p, signature_scheme: e.target.value as any }))}>
              <option value="none">None</option>
              <option value="github_hmac">GitHub HMAC-SHA256</option>
            </Select>
          </div>
          {form.signature_scheme === 'github_hmac' && (
            <div><Label>Secret {modal === 'edit' && <span className="text-slate-600">(blank = keep current)</span>}</Label>
              <Input type="password" value={form.secret ?? ''} onChange={e => setForm(p => ({ ...p, secret: e.target.value }))} placeholder="webhook-secret" /></div>
          )}
          <div><Label>Rate Limit (req/min)</Label>
            <Input type="number" value={form.rate_limit_per_minute} onChange={e => setForm(p => ({ ...p, rate_limit_per_minute: parseInt(e.target.value) }))} /></div>
          <div className="flex items-center gap-2">
            <input id="src_active" type="checkbox" checked={form.is_active}
              onChange={e => setForm(p => ({ ...p, is_active: e.target.checked }))}
              className="rounded border-[#245c2e] bg-[#183d21] text-green-600" />
            <Label htmlFor="src_active" className="mb-0">Active</Label>
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={() => setModal(null)}>Cancel</Button>
          <Button onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save'}</Button>
        </div>
      </Modal>

      <ConfirmDialog open={deleteId !== null} message="Delete this source? All associated routes will also be deleted."
        onConfirm={() => deleteId && deleteMut.mutate(deleteId)} onCancel={() => setDeleteId(null)} loading={deleteMut.isPending} />
    </div>
  )
}
