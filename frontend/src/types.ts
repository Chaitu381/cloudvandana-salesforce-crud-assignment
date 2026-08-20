export type ObjectName = 'Account' | 'Opportunity' | 'Lead' | 'Contact' | 'Case'

export interface AuthStatus {
  authenticated: boolean
  salesforceConfigured: boolean
  user: null | {
    displayName?: string
    username?: string
    userId?: string
    organizationId?: string
  }
}

export interface PicklistValue { label: string; value: string }

export interface FieldMeta {
  name: string
  label: string
  type: string
  createable: boolean
  updateable: boolean
  nillable: boolean
  defaultedOnCreate: boolean
  calculated: boolean
  length?: number | null
  precision?: number | null
  scale?: number | null
  referenceTo: string[]
  picklistValues: PicklistValue[]
}

export interface ObjectMetadata {
  name: ObjectName
  label: string
  fields: FieldMeta[]
  defaultFields: string[]
}

export type SfRecord = Record<string, unknown> & { Id: string }

export interface RecordPage {
  records: SfRecord[]
  nextCursor: string | null
  hasMore: boolean
}
