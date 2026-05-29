import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { routesApi, Route, CreateRoute, TRANSFORMER_CHOICES } from '@/api/routes'
import { sourcesApi } from '@/api/sources'
import { destinationsApi } from '@/api/destinations'
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

const emptyForm: CreateRoute = {
  source: 0, destination: 0, transformer_class: 'github_to_slack',
  event_type: '', condition: {}, priority: 0, is_active: true, rate_limit_per_minute: null,
}

export default function Routes() {
  const qc = useQueryClient()
  const [modal, setModal] = useState<'create' | 'edit' | null>(null)
  const [editing, setEditing] = useState<Route | null>(null)
  const [form, setForm] = useState<CreateRoute>(emptyForm)
  const [condRaw, setCondRaw] = useState('{}')
  const [condErr, setCondErr] = useState('')
  const [deleteId, setDeleteId] = useState<number | null>(null)

  const { data, isLoading } = useQuery({ queryKey: ['routes'], queryFn: () => routesApi.list() })
  const { data: sources } = useQuery({ queryKey: ['sources'], queryFn: sourcesApi.list })
  const { data: destinations } = useQuery({ queryKey: ['destinations'], queryFn: destinationsApi.list })
  const inv = () => qc.invalidateQueries({ queryKey: ['routes'] })

  const createMut = useMutation({ mutationFn: routesApi.create, onSuccess: () => { inv(); setModal(null) } })
  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<CreateRoute> }) => routesApi.update(id, data),
    onSuccess: () => { inv(); setModal(null) },
  })
  const deleteMut = useMutation({ mutationFn: routesApi.delete, onSuccess: () => { inv(); setDeleteId(null) } })
  const toggleMut = useMutation({ mutationFn: routesApi.toggleActive, onSuccess: inv })

  function openCreate() { setForm(emptyForm); setCondRaw('{}'); setCondErr(''); setModal('create') }
  function openEdit(r: Route) {
    setEditing(r)
    setForm({ source: r.source, destination: r.destination, transformer_class: r.transformer_class,
      event_type: r.event_type, condition: r.condition, priority: r.priority,
      is_active: r.is_active, rate_limit_per_minute: r.rate_limit_per_minute })
    setCondRaw(JSON.stringify(r.condition, null, 2)); setCondErr(''); setModal('edit')
  }
  function handleCond(raw: string) {
    setCondRaw(raw)
    try { setForm(p => ({ ...p, condition: JSON.parse(raw) })); setCondErr('') }
    catch { setCondErr('Invalid JSON') }
  }
  function save() {
    if (condErr) return
    if (modal === 'create') createMut.mutate(form)
    else if (editing) updateMut.mutate({ id: editing.id, data: form })
  }
  const saving = createMut.isPending || updateMut.isPending

  return (
    <div className="p-8">
      <PageHeader title="Routes" description="Rules that map a source + condition to a destination + transformer."
        action={<Button onClick={openCreate}><Icon name="add" size={16} />New Route</Button>} />

      {isLoading ? <div className="flex justify-center py-16"><Spinner size={24} /></div> : (
        <Card className="p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-[#1e3d24]">
              <tr>{['Priority', 'Source → Destination', 'Event Type', 'Transformer', 'Status', ''].map(h =>
                <th key={h} className="text-left px-5 py-3 text-xs font-medium text-slate-500">{h}</th>)}</tr>
            </thead>
            <tbody>
              {data?.results.map(r => (
                <tr key={r.id} className="border-b border-[#1e3d24]/50 hover:bg-[#183d21]/20 transition-colors">
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-500">{r.priority}</td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-1.5 text-xs">
                      <span className="text-slate-100">{r.source_name}</span>
                      <Icon name="arrow_forward" size={13} className="text-slate-600" />
                      <span className="text-slate-100">{r.destination_name}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-400">
                    {r.event_type || <span className="text-slate-600 italic">any</span>}
                  </td>
                  <td className="px-5 py-3.5"><Badge label={r.transformer_class_display} color="blue" /></td>
                  <td className="px-5 py-3.5"><Badge label={r.is_active ? 'active' : 'inactive'} color={r.is_active ? 'green' : 'gray'} /></td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-3 justify-end">
                      <button onClick={() => toggleMut.mutate(r.id)} className="text-slate-500 hover:text-green-400 transition-colors"><Icon name="power_settings_new" size={17} /></button>
                      <button onClick={() => openEdit(r)} className="text-slate-500 hover:text-blue-400 transition-colors"><Icon name="edit" size={17} /></button>
                      <button onClick={() => setDeleteId(r.id)} className="text-slate-500 hover:text-red-400 transition-colors"><Icon name="delete" size={17} /></button>
                    </div>
                  </td>
                </tr>
              ))}
              {!data?.results.length && (
                <tr><td colSpan={6} className="px-5 py-12 text-center text-slate-600">No routes yet. Create sources and destinations first.</td></tr>
              )}
            </tbody>
          </table>
        </Card>
      )}

      <Modal title={modal === 'create' ? 'New Route' : 'Edit Route'} open={modal !== null} onClose={() => setModal(null)} width="max-w-xl">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div><Label>Source</Label>
              <Select value={form.source || ''} onChange={e => setForm(p => ({ ...p, source: parseInt(e.target.value) }))}>
                <option value="">Select source…</option>
                {sources?.results.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </Select></div>
            <div><Label>Destination</Label>
              <Select value={form.destination || ''} onChange={e => setForm(p => ({ ...p, destination: parseInt(e.target.value) }))}>
                <option value="">Select destination…</option>
                {destinations?.results.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </Select></div>
          </div>
          <div><Label>Transformer</Label>
            <Select value={form.transformer_class} onChange={e => setForm(p => ({ ...p, transformer_class: e.target.value }))}>
              {TRANSFORMER_CHOICES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </Select></div>
          <div className="grid grid-cols-2 gap-4">
            <div><Label>Event Type <span className="text-slate-600">(blank = any)</span></Label>
              <Input value={form.event_type ?? ''} onChange={e => setForm(p => ({ ...p, event_type: e.target.value }))} placeholder="push" /></div>
            <div><Label>Priority <span className="text-slate-600">(lower = first)</span></Label>
              <Input type="number" value={form.priority ?? 0} onChange={e => setForm(p => ({ ...p, priority: parseInt(e.target.value) }))} /></div>
          </div>
          <div><Label>JSONPath Conditions <span className="text-slate-600">(JSON object)</span></Label>
            <textarea value={condRaw} onChange={e => handleCond(e.target.value)} rows={3}
              className="w-full rounded-md bg-[#183d21] border border-[#245c2e] text-slate-100 px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-green-500"
              placeholder='{"ref": "refs/heads/main"}' />
            {condErr && <p className="text-xs text-red-400 mt-1">{condErr}</p>}
          </div>
          <div><Label>Route Rate Limit/min <span className="text-slate-600">(blank = source default)</span></Label>
            <Input type="number" value={form.rate_limit_per_minute ?? ''} placeholder="Leave blank to inherit"
              onChange={e => setForm(p => ({ ...p, rate_limit_per_minute: e.target.value ? parseInt(e.target.value) : null }))} /></div>
          <div className="flex items-center gap-2">
            <input id="route_active" type="checkbox" checked={form.is_active ?? true}
              onChange={e => setForm(p => ({ ...p, is_active: e.target.checked }))}
              className="rounded border-[#245c2e] bg-[#183d21] text-green-600" />
            <Label htmlFor="route_active" className="mb-0">Active</Label>
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={() => setModal(null)}>Cancel</Button>
          <Button onClick={save} disabled={saving || !!condErr}>{saving ? 'Saving…' : 'Save'}</Button>
        </div>
      </Modal>

      <ConfirmDialog open={deleteId !== null} message="Delete this route?"
        onConfirm={() => deleteId && deleteMut.mutate(deleteId)} onCancel={() => setDeleteId(null)} loading={deleteMut.isPending} />
    </div>
  )
}
