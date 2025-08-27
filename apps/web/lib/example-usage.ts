/**
 * Example usage of the new type-safe API system
 * This file demonstrates how to use the types, schemas, and logo system
 */

import { assertAskResponse } from './zod';
import { getSourceLogo, getSourceLogos } from './logos';
import type { AskResponse, Source } from './types';

// Example: Processing API response with validation
export async function handleApiResponse(rawResponse: unknown): Promise<AskResponse> {
  // This will throw if the response doesn't match our schema
  const validatedResponse = assertAskResponse(rawResponse);
  
  // Now we have fully typed, validated data
  console.log(`Intent: ${validatedResponse.metrics.intent}`);
  console.log(`Confidence: ${validatedResponse.metrics.confidence}`);
  console.log(`Sources: ${validatedResponse.sources.length}`);
  
  return validatedResponse;
}

// Example: Enriching sources with logos
export function enrichSourcesWithLogos(sources: Source[]): (Source & { logo: string })[] {
  return sources.map(source => ({
    ...source,
    logo: getSourceLogo(source.name)
  }));
}

// Example: Batch logo loading for multiple sources
export function preloadSourceLogos(sourceNames: string[]): Record<string, string> {
  return getSourceLogos(sourceNames);
}

// Example: Mock response for testing
export const MOCK_ASK_RESPONSE: AskResponse = {
  answer_bn: "এটি একটি পরীক্ষার উত্তর।",
  answer_en: "This is a test answer.",
  sources: [
    {
      name: "Reuters",
      url: "https://reuters.com/article/123",
      published_at: "2024-01-01T12:00:00Z"
    },
    {
      name: "BBC",
      url: "https://bbc.com/news/456", 
      published_at: "2024-01-01T11:30:00Z"
    }
  ],
  flags: {
    disagreement: false,
    single_source: false
  },
  metrics: {
    latency_ms: 1250,
    source_count: 2,
    updated_ct: "2024-01-01T12:00:00Z",
    intent: "news",
    confidence: 0.95
  },
  followups: [
    "Tell me more about this topic",
    "What are the latest developments?"
  ]
};

// Example validation - this would throw if MOCK_ASK_RESPONSE was invalid
assertAskResponse(MOCK_ASK_RESPONSE);