import { z } from "zod";
import type { AskResponse } from "./types";

export const SourceSchema = z.object({
  name: z.string(),
  url: z.string(),
  published_at: z.string().nullable().optional(),
  logo: z.string().nullable().optional(),
});

export const FlagsSchema = z.object({
  disagreement: z.boolean(),
  single_source: z.boolean(),
});

export const MetricsSchema = z.object({
  latency_ms: z.number().optional(),
  source_count: z.number(),
  updated_ct: z.string(),
  intent: z.string().optional(),
  confidence: z.number().optional(),
});

export const AskResponseSchema = z.object({
  answer_bn: z.string(),
  answer_en: z.string().optional(),
  sources: z.array(SourceSchema),
  flags: FlagsSchema,
  metrics: MetricsSchema,
  followups: z.array(z.string()).optional(),
});

export const AskRequestSchema = z.object({
  query: z.string().min(1, "Query cannot be empty"),
  lang: z.string().optional(),
});

export const ApiErrorSchema = z.object({
  error: z.string(),
  message: z.string().optional(),
  details: z.string().optional(),
});

/**
 * Validates and parses JSON response from backend API
 * @param json - Raw JSON response from backend
 * @returns Parsed and validated AskResponse
 * @throws ZodError if validation fails
 */
export function assertAskResponse(json: unknown): AskResponse {
  try {
    return AskResponseSchema.parse(json);
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error("Invalid API response structure:", error.errors);
      throw new Error(`Invalid API response: ${error.errors.map(e => e.message).join(", ")}`);
    }
    throw error;
  }
}

/**
 * Validates ask request before sending to API
 */
export function assertAskRequest(data: unknown) {
  try {
    return AskRequestSchema.parse(data);
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error("Invalid request data:", error.errors);
      throw new Error(`Invalid request: ${error.errors.map(e => e.message).join(", ")}`);
    }
    throw error;
  }
}

/**
 * Type guards for runtime type checking
 */
export function isApiError(data: unknown): data is z.infer<typeof ApiErrorSchema> {
  return ApiErrorSchema.safeParse(data).success;
}

export function isAskResponse(data: unknown): data is AskResponse {
  return AskResponseSchema.safeParse(data).success;
}