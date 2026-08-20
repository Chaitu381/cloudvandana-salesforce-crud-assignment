import { useMemo, useState } from 'react'
import type { FieldMeta } from '../types'
import { FilterIcon, XIcon } from './Icons'

export function FieldSelector({ fields, selected, onApply }: { fields: FieldMeta[]; selected: string[]; onApply: (fields: string[]) => void }) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState(selected)
  const [search, setSearch] = useState('')
  const visible = useMemo(() => fields.filter(f => f.name !== 'Id' && f.name !== 'CreatedDate' && `${f.label} ${f.name}`.toLowerCase().includes(search.toLowerCase())), [fields, search])

  function toggle(name: string) {
    setDraft(current => current.includes(name) ? current.filter(v => v !== name) : current.length < 10 ? [...current, name] : current)
  }
  function show() { setDraft(selected); setOpen(true) }
  function apply() { if (draft.length >= 5 && draft.length <= 10) { onApply(draft); setOpen(false) } }

  return <>
    <button className="button secondary" onClick={show}><FilterIcon /> Fields <span className="count-pill">{selected.length}</span></button>
    {open && <div className="drawer-backdrop" onMouseDown={e => e.target === e.currentTarget && setOpen(false)}>
      <aside className="field-drawer">
        <header><div><h3>Choose fields</h3><p>Select 5–10 columns to display.</p></div><button className="icon-button" onClick={() => setOpen(false)}><XIcon /></button></header>
        <div className="field-search"><input placeholder="Search fields…" value={search} onChange={e => setSearch(e.target.value)} /></div>
        <div className="field-list">{visible.map(field => <label key={field.name}><input type="checkbox" checked={draft.includes(field.name)} onChange={() => toggle(field.name)} disabled={!draft.includes(field.name) && draft.length >= 10} /><span><b>{field.label}</b><small>{field.name} · {field.type}</small></span></label>)}</div>
        <footer><span className={draft.length < 5 ? 'warning-text' : ''}>{draft.length}/10 selected{draft.length < 5 ? ' · choose at least 5' : ''}</span><button className="button primary" disabled={draft.length < 5 || draft.length > 10} onClick={apply}>Apply fields</button></footer>
      </aside>
    </div>}
  </>
}
