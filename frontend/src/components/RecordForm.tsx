import { useMemo, useState } from 'react'
import type { FieldMeta, SfRecord } from '../types'

function inputType(field: FieldMeta) {
  if (field.type === 'email') return 'email'
  if (field.type === 'url') return 'url'
  if (field.type === 'phone') return 'tel'
  if (field.type === 'date') return 'date'
  if (field.type === 'datetime') return 'datetime-local'
  if (['currency', 'double', 'int', 'percent'].includes(field.type)) return 'number'
  return 'text'
}

function initialValue(field: FieldMeta, record?: SfRecord) {
  const value = record?.[field.name]
  if (value === null || value === undefined) return field.type === 'boolean' ? false : ''
  if (field.type === 'datetime' && typeof value === 'string') {
    const d = new Date(value)
    if (!Number.isNaN(d.valueOf())) return d.toISOString().slice(0, 16)
  }
  return value as string | number | boolean
}

export function RecordForm({ fields, record, mode, busy, onSubmit, onCancel }: {
  fields: FieldMeta[]
  record?: SfRecord
  mode: 'create' | 'edit'
  busy: boolean
  onSubmit: (values: Record<string, unknown>) => Promise<void>
  onCancel: () => void
}) {
  const editable = useMemo(() => fields.filter(f => mode === 'create' ? f.createable : f.updateable), [fields, mode])
  const [values, setValues] = useState<Record<string, string | number | boolean>>(() => Object.fromEntries(editable.map(f => [f.name, initialValue(f, record)])))

  const required = (field: FieldMeta) => mode === 'create' && !field.nillable && !field.defaultedOnCreate && !field.calculated

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const payload: Record<string, unknown> = {}
    for (const field of editable) {
      const raw = values[field.name]
      if (field.type === 'boolean') { payload[field.name] = Boolean(raw); continue }
      if (raw === '') {
        if (mode === 'edit') payload[field.name] = null
        continue
      }
      if (['currency', 'double', 'int', 'percent'].includes(field.type)) payload[field.name] = Number(raw)
      else if (field.type === 'datetime' && typeof raw === 'string') payload[field.name] = new Date(raw).toISOString()
      else payload[field.name] = raw
    }
    await onSubmit(payload)
  }

  return <form onSubmit={submit}>
    <div className="modal-body form-grid">
      {editable.map(field => <label key={field.name} className={field.type === 'textarea' ? 'span-2' : ''}>
        <span>{field.label}{required(field) && <b className="required"> *</b>}</span>
        {field.type === 'boolean' ? <div className="checkbox-input"><input type="checkbox" checked={Boolean(values[field.name])} onChange={e => setValues(v => ({ ...v, [field.name]: e.target.checked }))} /><em>Enabled</em></div>
          : field.type === 'textarea' ? <textarea required={required(field)} value={String(values[field.name] ?? '')} maxLength={field.length ?? undefined} onChange={e => setValues(v => ({ ...v, [field.name]: e.target.value }))} />
          : ['picklist', 'combobox'].includes(field.type) && field.picklistValues.length ? <select required={required(field)} value={String(values[field.name] ?? '')} onChange={e => setValues(v => ({ ...v, [field.name]: e.target.value }))}><option value="">Select…</option>{field.picklistValues.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}</select>
          : <input required={required(field)} type={inputType(field)} step={field.type === 'int' ? 1 : ['currency', 'double', 'percent'].includes(field.type) ? 'any' : undefined} value={String(values[field.name] ?? '')} maxLength={field.length ?? undefined} placeholder={field.type === 'reference' ? `${field.referenceTo.join(' / ') || 'Salesforce'} record ID` : undefined} onChange={e => setValues(v => ({ ...v, [field.name]: e.target.value }))} />}
        <small>{field.name}{field.type === 'reference' && field.referenceTo.length ? ` · ${field.referenceTo.join(', ')}` : ''}</small>
      </label>)}
      {!editable.length && <p className="empty-state">No editable fields are available for this selection.</p>}
    </div>
    <footer className="modal-footer"><button type="button" className="button secondary" onClick={onCancel}>Cancel</button><button className="button primary" disabled={busy || !editable.length}>{busy ? 'Saving…' : mode === 'create' ? 'Create record' : 'Save changes'}</button></footer>
  </form>
}
