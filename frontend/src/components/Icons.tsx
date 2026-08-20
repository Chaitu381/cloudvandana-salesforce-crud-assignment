import type { SVGProps } from 'react'

function IconBase({ children, ...props }: SVGProps<SVGSVGElement>) {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{children}</svg>
}
export const PlusIcon = (p: SVGProps<SVGSVGElement>) => <IconBase {...p}><path d="M12 5v14M5 12h14" /></IconBase>
export const EyeIcon = (p: SVGProps<SVGSVGElement>) => <IconBase {...p}><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6S2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="2.5"/></IconBase>
export const EditIcon = (p: SVGProps<SVGSVGElement>) => <IconBase {...p}><path d="m4 20 4.2-1 10-10a2.1 2.1 0 0 0-3-3l-10 10L4 20Z"/><path d="m13.8 7.2 3 3"/></IconBase>
export const TrashIcon = (p: SVGProps<SVGSVGElement>) => <IconBase {...p}><path d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13M10 11v5M14 11v5"/></IconBase>
export const ChevronIcon = (p: SVGProps<SVGSVGElement>) => <IconBase {...p}><path d="m7 10 5 5 5-5"/></IconBase>
export const FilterIcon = (p: SVGProps<SVGSVGElement>) => <IconBase {...p}><path d="M4 5h16M7 12h10M10 19h4"/></IconBase>
export const LogoutIcon = (p: SVGProps<SVGSVGElement>) => <IconBase {...p}><path d="M10 17l5-5-5-5M15 12H3M14 4h5a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-5"/></IconBase>
export const XIcon = (p: SVGProps<SVGSVGElement>) => <IconBase {...p}><path d="M6 6l12 12M18 6 6 18"/></IconBase>
export const CloudIcon = (p: SVGProps<SVGSVGElement>) => <IconBase {...p}><path d="M17.5 19H7a5 5 0 0 1-.8-9.94A7 7 0 0 1 19.6 11 4 4 0 0 1 17.5 19Z"/></IconBase>
