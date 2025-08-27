export interface AskRequest {
  query: string
  lang?: string
}

export interface SourceInfo {
  name: string
  url: string
  published_at?: string
}

export interface AskResponse {
  answer_bn: string
  sources: SourceInfo[]
  metrics: {
    intent: string
    confidence: number
    latency_ms: number
    source_count: number
    updated_ct: string
  }
  flags: {
    single_source: boolean
    disagreement: boolean
  }
  router_info: string
}

export interface ApiError {
  error: string
  message?: string
  details?: string
}