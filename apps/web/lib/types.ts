export type Source = {
  name: string;
  url: string;
  published_at?: string | null;
  logo?: string | null;
};

export type Flags = {
  disagreement: boolean;
  single_source: boolean;
};

export type Metrics = {
  latency_ms?: number;
  source_count: number;
  updated_ct: string;
  intent?: string;
  confidence?: number;
};

export type AskResponse = {
  answer_bn: string;
  answer_en?: string;
  sources: Source[];
  flags: Flags;
  metrics: Metrics;
  followups?: string[];
};

export type AskRequest = {
  query: string;
  lang?: string;
};

export type ApiError = {
  error: string;
  message?: string;
  details?: string;
};