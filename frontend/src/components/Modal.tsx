import type { ReactNode } from 'react'
import { XIcon } from './Icons'

export function Modal({ title, subtitle, children, onClose, width = 720 }: { title: string; subtitle?: string; children: ReactNode; onClose: () => void; width?: number }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
    <section className="modal" style={{ maxWidth: width }} role="dialog" aria-modal="true" aria-label={title}>
      <header className="modal-header">
        <div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>
        <button className="icon-button" onClick={onClose} aria-label="Close"><XIcon /></button>
      </header>
      {children}
    </section>
  </div>
}
