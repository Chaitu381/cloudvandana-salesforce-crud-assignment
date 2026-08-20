import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, ApiError } from './lib/api'
import type { AuthStatus, FieldMeta, ObjectMetadata, ObjectName, SfRecord } from './types'
import { ChevronIcon, CloudIcon, EditIcon, EyeIcon, LogoutIcon, PlusIcon, TrashIcon } from './components/Icons'
import { FieldSelector } from './components/FieldSelector'
import { Modal } from './components/Modal'
import { RecordForm } from './components/RecordForm'

const OBJECTS: ObjectName[] = ['Account', 'Opportunity', 'Lead', 'Contact', 'Case']

function errorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return 'Something went wrong'
}

function Login({ configured }: { configured: boolean }) {
  const oauthError = new URLSearchParams(location.search).get('oauth_error')
  return <main className="login-shell">
    <section className="login-card">
      <div className="brand-mark large"><CloudIcon /></div>
      <span className="eyebrow">CloudVandana Assignment</span>
      <h1>Salesforce Object Manager</h1>
      <p>Securely manage standard Salesforce records from one focused workspace—without opening the native Salesforce interface.</p>
      {oauthError && <div className="alert error">Salesforce login failed: {oauthError}</div>}
      {!configured && <div className="alert warning">Salesforce OAuth is not configured on this server yet. Add the External Client App credentials to the environment.</div>}
      <button className="button salesforce-login" disabled={!configured} onClick={() => { location.href = '/api/auth/login' }}><CloudIcon /> Log in with Salesforce</button>
      <div className="login-features"><span>OAuth 2.0 + PKCE</span><span>Encrypted session</span><span>5 standard objects</span></div>
    </section>
  </main>
}

function valueText(value: unknown) {
  if (value === null || value === undefined || value === '') return <span className="muted">—</span>
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export default function App() {
  const [auth, setAuth] = useState<AuthStatus | null>(null)
  const [objectName, setObjectName] = useState<ObjectName>('Account')
  const [metadata, setMetadata] = useState<ObjectMetadata | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [records, setRecords] = useState<SfRecord[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState('')
  const [modal, setModal] = useState<{ mode: 'view' | 'create' | 'edit' | 'delete'; record?: SfRecord } | null>(null)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState('')
  const sentinel = useRef<HTMLDivElement | null>(null)

  useEffect(() => { api.authStatus().then(setAuth).catch(() => setAuth({ authenticated: false, salesforceConfigured: false, user: null })) }, [])

  const loadPage = useCallback(async (obj: ObjectName, fields: string[], pageCursor: string | null, append: boolean) => {
    if (!fields.length) return
    append ? setLoadingMore(true) : setLoading(true)
    setError('')
    try {
      const page = await api.records(obj, fields, pageCursor)
      setRecords(current => append ? [...current, ...page.records] : page.records)
      setCursor(page.nextCursor)
      setHasMore(page.hasMore)
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) { setAuth(a => a ? { ...a, authenticated: false } : a); return }
      setError(errorMessage(e))
    } finally { append ? setLoadingMore(false) : setLoading(false) }
  }, [])

  useEffect(() => {
    if (!auth?.authenticated) return
    setLoading(true); setError(''); setMetadata(null); setRecords([])
    api.metadata(objectName).then(meta => {
      setMetadata(meta)
      const saved = localStorage.getItem(`sf-fields:${objectName}`)
      let fields = meta.defaultFields
      if (saved) {
        try {
          const parsed = JSON.parse(saved) as string[]
          const available = new Set(meta.fields.map(f => f.name))
          const valid = parsed.filter(f => available.has(f))
          if (valid.length >= 5 && valid.length <= 10) fields = valid
        } catch { /* ignore invalid local preference */ }
      }
      setSelected(fields)
      return loadPage(objectName, fields, null, false)
    }).catch(e => { setError(errorMessage(e)); setLoading(false) })
  }, [auth?.authenticated, objectName, loadPage])

  useEffect(() => {
    const node = sentinel.current
    if (!node || !hasMore || loading || loadingMore) return
    const observer = new IntersectionObserver(entries => {
      if (entries[0]?.isIntersecting && cursor) void loadPage(objectName, selected, cursor, true)
    }, { rootMargin: '180px' })
    observer.observe(node)
    return () => observer.disconnect()
  }, [cursor, hasMore, loading, loadingMore, loadPage, objectName, selected])

  const fieldMap = useMemo(() => new Map(metadata?.fields.map(f => [f.name, f]) ?? []), [metadata])
  const selectedMeta = useMemo(() => selected.map(name => fieldMap.get(name)).filter(Boolean) as FieldMeta[], [selected, fieldMap])
  const createFields = useMemo(() => {
    if (!metadata) return []
    const required = metadata.fields.filter(f => f.createable && !f.nillable && !f.defaultedOnCreate && !f.calculated)
    const chosen = selectedMeta.filter(f => f.createable)
    return Array.from(new Map([...required, ...chosen].map(f => [f.name, f])).values())
  }, [metadata, selectedMeta])

  function applyFields(fields: string[]) {
    localStorage.setItem(`sf-fields:${objectName}`, JSON.stringify(fields))
    setSelected(fields); setRecords([]); setCursor(null); void loadPage(objectName, fields, null, false)
  }

  async function logout() { await api.logout().catch(() => undefined); setAuth(a => a ? { ...a, authenticated: false, user: null } : a) }
  function notify(message: string) { setToast(message); window.setTimeout(() => setToast(''), 2800) }

  async function create(values: Record<string, unknown>) {
    setSaving(true)
    try { await api.create(objectName, values); setModal(null); notify('Record created'); await loadPage(objectName, selected, null, false) }
    catch (e) { setError(errorMessage(e)) } finally { setSaving(false) }
  }
  async function update(values: Record<string, unknown>) {
    if (!modal?.record) return
    setSaving(true)
    try { await api.update(objectName, modal.record.Id, values); setModal(null); notify('Record updated'); await loadPage(objectName, selected, null, false) }
    catch (e) { setError(errorMessage(e)) } finally { setSaving(false) }
  }
  async function remove() {
    if (!modal?.record) return
    setSaving(true)
    try { await api.delete(objectName, modal.record.Id); setModal(null); notify('Record deleted'); await loadPage(objectName, selected, null, false) }
    catch (e) { setError(errorMessage(e)) } finally { setSaving(false) }
  }

  if (!auth) return <main className="center-screen"><div className="loader" /></main>
  if (!auth.authenticated) return <Login configured={auth.salesforceConfigured} />

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><CloudIcon /></div><div><strong>Salesforce Object Manager</strong><span>Standard Object CRUD Workspace</span></div></div>
      <div className="user-area"><div className="user-copy"><b>{auth.user?.displayName || auth.user?.username || 'Salesforce User'}</b><span>{auth.user?.username || 'Connected'}</span></div><button className="icon-button" title="Log out" onClick={logout}><LogoutIcon /></button></div>
    </header>

    <main className="workspace">
      <section className="hero-row">
        <div><span className="eyebrow">Connected to Salesforce</span><h1>Manage {objectName} records</h1><p>Choose an object, select 5–10 fields, and create, inspect, update, or delete records.</p></div>
        <div className="toolbar">
          <div className="select-wrap"><select value={objectName} onChange={e => setObjectName(e.target.value as ObjectName)}>{OBJECTS.map(o => <option key={o}>{o}</option>)}</select><ChevronIcon /></div>
          {metadata && <FieldSelector fields={metadata.fields} selected={selected} onApply={applyFields} />}
          <button className="button primary" disabled={!metadata} onClick={() => setModal({ mode: 'create' })}><PlusIcon /> New {objectName}</button>
        </div>
      </section>

      {error && <div className="alert error dismissible"><span>{error}</span><button onClick={() => setError('')}>×</button></div>}
      <section className="table-card">
        <div className="table-header"><div><b>{objectName}</b><span>{records.length} loaded</span></div><span className="page-size">20 records per page</span></div>
        <div className="table-scroll">
          <table><thead><tr>{selected.map(name => <th key={name}>{fieldMap.get(name)?.label ?? name}<small>{name}</small></th>)}<th className="actions-column">Actions</th></tr></thead>
            <tbody>{loading ? Array.from({ length: 6 }).map((_, i) => <tr key={i} className="skeleton-row">{selected.map(f => <td key={f}><i /></td>)}<td><i /></td></tr>)
              : records.length ? records.map(record => <tr key={record.Id}>{selected.map(name => <td key={name}>{valueText(record[name])}</td>)}<td className="actions"><button title="View" onClick={() => setModal({ mode: 'view', record })}><EyeIcon /></button><button title="Edit" onClick={() => setModal({ mode: 'edit', record })}><EditIcon /></button><button className="danger-icon" title="Delete" onClick={() => setModal({ mode: 'delete', record })}><TrashIcon /></button></td></tr>)
              : <tr><td colSpan={selected.length + 1}><div className="empty-state"><CloudIcon /><b>No {objectName.toLowerCase()} records found</b><span>Create the first record or choose another object.</span></div></td></tr>}</tbody>
          </table>
        </div>
        <div ref={sentinel} className="load-sentinel">{loadingMore && <><div className="loader small" /> Loading next 20…</>}{!hasMore && records.length > 0 && !loading && <span>End of records</span>}</div>
      </section>
    </main>

    {modal?.mode === 'view' && modal.record && <Modal title={`${objectName} details`} subtitle={modal.record.Id} onClose={() => setModal(null)}><div className="modal-body detail-grid">{selectedMeta.map(field => <div key={field.name}><span>{field.label}</span><b>{valueText(modal.record?.[field.name])}</b><small>{field.name}</small></div>)}</div><footer className="modal-footer"><button className="button secondary" onClick={() => setModal(null)}>Close</button><button className="button primary" onClick={() => setModal({ mode: 'edit', record: modal.record })}><EditIcon /> Edit</button></footer></Modal>}
    {modal?.mode === 'create' && <Modal title={`Create ${objectName}`} subtitle="Required Salesforce fields are included automatically." onClose={() => setModal(null)}><RecordForm fields={createFields} mode="create" busy={saving} onSubmit={create} onCancel={() => setModal(null)} /></Modal>}
    {modal?.mode === 'edit' && modal.record && <Modal title={`Edit ${objectName}`} subtitle={modal.record.Id} onClose={() => setModal(null)}><RecordForm fields={selectedMeta} record={modal.record} mode="edit" busy={saving} onSubmit={update} onCancel={() => setModal(null)} /></Modal>}
    {modal?.mode === 'delete' && modal.record && <Modal title={`Delete ${objectName}?`} subtitle="This action is sent directly to Salesforce." onClose={() => setModal(null)} width={520}><div className="modal-body"><div className="delete-warning"><TrashIcon /><div><b>This cannot be undone here.</b><p>Record ID: <code>{modal.record.Id}</code></p></div></div></div><footer className="modal-footer"><button className="button secondary" onClick={() => setModal(null)}>Cancel</button><button className="button danger" disabled={saving} onClick={remove}>{saving ? 'Deleting…' : 'Delete record'}</button></footer></Modal>}
    {toast && <div className="toast">✓ {toast}</div>}
  </div>
}
