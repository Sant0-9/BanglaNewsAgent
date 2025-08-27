import { assertAskResponse, assertAskRequest } from './zod';
import type { AskResponse, AskRequest } from './types';
import { API_BASE } from './config';

/**
 * Extended request body for API calls
 */
export interface PostAskBody {
  query: string;
  lang: 'bn' | 'en';
  mode?: 'brief' | 'deep';
  window_hours?: number;
}

/**
 * Streaming chunk interface for SSE responses
 */
export interface StreamChunk {
  type: 'token' | 'sources' | 'complete' | 'error';
  data: any;
  delta?: string; // For token streaming
}

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly code?: string,
    public readonly status?: number,
    public readonly details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Custom error class for timeout errors
 */
export class TimeoutError extends ApiError {
  constructor(message: string = 'Request timed out') {
    super(message, 'TIMEOUT', 408);
    this.name = 'TimeoutError';
  }
}

/**
 * Custom error class for abort errors
 */
export class AbortError extends ApiError {
  constructor(message: string = 'Request was aborted') {
    super(message, 'ABORTED', 0);
    this.name = 'AbortError';
  }
}

/**
 * Configuration for the API client
 */
export interface ApiConfig {
  baseUrl?: string;
  timeout?: number;
  retryAttempts?: number;
}

/**
 * Default configuration
 */
const DEFAULT_CONFIG: Required<ApiConfig> = {
  baseUrl: API_BASE,
  timeout: 20000, // 20 seconds
  retryAttempts: 1,
};

/**
 * Parse Server-Sent Events stream
 */
async function parseSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onChunk?: (chunk: StreamChunk) => void,
  signal?: AbortSignal
): Promise<AskResponse> {
  const decoder = new TextDecoder();
  let buffer = '';
  let finalResponse: Partial<AskResponse> = {
    answer_bn: '',
    sources: [],
    flags: { disagreement: false, single_source: false },
    metrics: { source_count: 0, updated_ct: new Date().toISOString() }
  };

  try {
    while (true) {
      if (signal?.aborted) {
        throw new AbortError();
      }

      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim() || !line.startsWith('data: ')) continue;
        
        try {
          const data = line.slice(6); // Remove 'data: ' prefix
          if (data === '[DONE]') {
            // Stream complete
            if (onChunk) {
              onChunk({ type: 'complete', data: finalResponse });
            }
            return assertAskResponse(finalResponse);
          }

          const chunk: StreamChunk = JSON.parse(data);
          
          // Process different chunk types
          switch (chunk.type) {
            case 'token':
              if (chunk.delta) {
                finalResponse.answer_bn += chunk.delta;
              }
              break;
            case 'sources':
              finalResponse.sources = chunk.data;
              break;
            case 'complete':
              finalResponse = { ...finalResponse, ...chunk.data };
              break;
            case 'error':
              throw new ApiError(chunk.data.message || 'Stream error', 'STREAM_ERROR');
          }

          if (onChunk) {
            onChunk(chunk);
          }

        } catch (parseError) {
          console.warn('Failed to parse SSE chunk:', line, parseError);
        }
      }
    }

    return assertAskResponse(finalResponse);

  } finally {
    reader.releaseLock();
  }
}

/**
 * Make a request with timeout and abort support
 */
async function makeRequest(
  url: string,
  options: RequestInit,
  timeout: number,
  signal?: AbortSignal
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  // If an external signal is provided, forward its abort to our controller
  const handleExternalAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) {
      clearTimeout(timeoutId);
      throw new AbortError('Request was cancelled');
    }
    signal.addEventListener('abort', handleExternalAbort, { once: true });
  }

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    return response;

  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof DOMException && error.name === 'AbortError') {
      if (signal?.aborted) {
        throw new AbortError('Request was cancelled');
      }
      throw new TimeoutError('Request timed out');
    }

    throw error;
  } finally {
    if (signal) {
      signal.removeEventListener('abort', handleExternalAbort as EventListener);
    }
  }
}

/**
 * Attempt SSE streaming request
 */
async function trySSEStream(
  body: PostAskBody,
  config: Required<ApiConfig>,
  onChunk?: (chunk: StreamChunk) => void,
  signal?: AbortSignal
): Promise<AskResponse> {
  const validatedBody = assertAskRequest(body);
  
  const response = await makeRequest(
    `${config.baseUrl}/ask/stream`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(validatedBody),
    },
    config.timeout,
    signal
  );

  if (!response.ok) {
    if (response.status === 404) {
      throw new ApiError('SSE endpoint not available', 'SSE_NOT_AVAILABLE', 404);
    }
    
    // Don't read the response body here to avoid "body stream already read" error
    throw new ApiError(
      `SSE request failed: ${response.statusText}`,
      'SSE_REQUEST_FAILED',
      response.status
    );
  }

  if (!response.body) {
    throw new ApiError('No response body received', 'NO_RESPONSE_BODY');
  }

  // Only read the stream, never call .text() or .json() on this response
  const reader = response.body.getReader();
  return await parseSSEStream(reader, onChunk, signal);
}

/**
 * Fallback to regular JSON request
 */
async function tryJSONRequest(
  body: PostAskBody,
  config: Required<ApiConfig>,
  signal?: AbortSignal
): Promise<AskResponse> {
  const validatedBody = assertAskRequest(body);
  
  const response = await makeRequest(
    `${config.baseUrl}/ask`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(validatedBody),
    },
    config.timeout,
    signal
  );

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    let errorData = null;

    try {
      errorData = await response.json();
      errorMessage = errorData.error || errorData.message || errorMessage;
    } catch {
      errorMessage = await response.text() || errorMessage;
    }

    throw new ApiError(errorMessage, 'JSON_REQUEST_FAILED', response.status, errorData);
  }

  const data = await response.json();
  return assertAskResponse(data);
}

/**
 * Main API function that tries SSE first, then falls back to JSON
 */
export async function postAsk(
  body: PostAskBody,
  options: {
    onChunk?: (chunk: StreamChunk) => void;
    onDelta?: (delta: string) => void;
    signal?: AbortSignal;
    config?: Partial<ApiConfig>;
  } = {}
): Promise<AskResponse> {
  const { onChunk, onDelta, signal, config: userConfig } = options;
  const config = { ...DEFAULT_CONFIG, ...userConfig };

  // Create combined chunk handler that calls both onChunk and onDelta
  const combinedChunkHandler = onChunk || onDelta ? (chunk: StreamChunk) => {
    if (onChunk) {
      onChunk(chunk);
    }
    if (onDelta && chunk.type === 'token' && chunk.delta) {
      onDelta(chunk.delta);
    }
  } : undefined;

  try {
    // First, try SSE streaming
    return await trySSEStream(body, config, combinedChunkHandler, signal);
    
  } catch (sseError) {
    // If SSE is not available (404) or other SSE-specific errors, fallback to JSON
    if (sseError instanceof ApiError && 
        (sseError.code === 'SSE_NOT_AVAILABLE' || sseError.status === 404)) {
      
      console.info('SSE not available, falling back to JSON');
      
      try {
        return await tryJSONRequest(body, config, signal);
      } catch (jsonError) {
        // If JSON also fails, throw the JSON error (more likely to be actionable)
        throw jsonError;
      }
    }

    // For other SSE errors (timeout, abort, etc.), don't fallback
    throw sseError;
  }
}

/**
 * Convenience function for simple queries
 */
export async function askQuery(
  query: string,
  lang: 'bn' | 'en' = 'bn',
  options: {
    mode?: 'brief' | 'deep';
    window_hours?: number;
    onChunk?: (chunk: StreamChunk) => void;
    onDelta?: (delta: string) => void;
    signal?: AbortSignal;
    config?: Partial<ApiConfig>;
  } = {}
): Promise<AskResponse> {
  const { mode, window_hours, ...restOptions } = options;
  
  return postAsk(
    { query, lang, mode, window_hours },
    restOptions
  );
}

/**
 * Health check function
 */
export async function checkApiHealth(config?: Partial<ApiConfig>): Promise<boolean> {
  const finalConfig = { ...DEFAULT_CONFIG, ...config };
  
  try {
    const response = await makeRequest(
      `${finalConfig.baseUrl}/healthz`,
      { method: 'GET' },
      5000 // Shorter timeout for health check
    );
    return response.ok;
  } catch {
    return false;
  }
}