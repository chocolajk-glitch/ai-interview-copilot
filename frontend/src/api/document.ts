import { del, get, post } from './http'

export type DocStatus = 'pending' | 'processing' | 'ready' | 'failed' | 'duplicate'

export interface DocumentInfo {
  doc_id: string
  status: DocStatus
  filename: string
  chunk_count: number
  new_chunks: number
  skipped_chunks: number
  error: string | null
  created_at: string
}

export interface DocumentListResponse {
  total: number
  documents: DocumentInfo[]
}

export interface DocumentUploadResponse {
  status: DocStatus
  doc_id: string
  message: string
}

export const documentApi = {
  list: () => get<DocumentListResponse>('/api/document'),
  status: (docId: string) => get<DocumentInfo>(`/api/document/${docId}/status`),
  delete: (docId: string) => del<{ message: string; doc_id: string }>(`/api/document/${docId}`),
  upload: async (file: File): Promise<DocumentUploadResponse> => {
    const buf = await file.arrayBuffer()
    const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)))
    return post<DocumentUploadResponse>('/api/document/upload', {
      filename: file.name,
      content_b64: b64,
    })
  },
}

export const ACCEPTED_EXTS = ['.md', '.markdown', '.pdf', '.html', '.htm', '.txt']
export const ACCEPTED_MIMES = [
  'text/markdown',
  'text/plain',
  'text/html',
  'application/pdf',
]
export const MAX_FILE_SIZE = 20 * 1024 * 1024 // 20MB
