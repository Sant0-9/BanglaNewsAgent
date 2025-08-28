import { NextRequest, NextResponse } from 'next/server'
import { API_BASE } from '../../../lib/config'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // Validate request body
    if (!body.query || typeof body.query !== 'string') {
      return NextResponse.json(
        { error: 'Query is required and must be a string' },
        { status: 400 }
      )
    }

    // Add unique request ID and timestamp to prevent caching issues
    const requestId = crypto.randomUUID()
    const timestamp = Date.now()
    
    console.log(`[${requestId}] Processing query: "${body.query}" (lang: ${body.lang || 'bn'}, mode: ${body.mode || 'brief'})`)

    // Forward request to Python API with anti-cache headers
    const response = await fetch(`${API_BASE}/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'X-Request-ID': requestId,
        'X-Timestamp': timestamp.toString(),
      },
      body: JSON.stringify({
        query: body.query,
        lang: body.lang || 'bn',
        mode: body.mode || 'brief',
        window_hours: body.window_hours,
        request_id: requestId,
        timestamp: timestamp
      })
    })

    if (!response.ok) {
      let errorData: any
      let errorMessage = 'Backend API error'
      
      try {
        const contentType = response.headers.get('content-type')
        if (contentType?.includes('application/json')) {
          errorData = await response.json()
          errorMessage = errorData.error || errorData.message || errorMessage
        } else {
          errorData = await response.text()
          errorMessage = errorData || errorMessage
        }
      } catch (parseError) {
        console.error(`[${requestId}] Failed to parse error response:`, parseError)
      }
      
      console.error(`[${requestId}] API Error (${response.status}):`, errorMessage)
      
      return NextResponse.json(
        { 
          error: errorMessage,
          details: response.status === 404 ? 'API endpoint not found' : 
                   response.status === 429 ? 'Rate limit exceeded' :
                   response.status === 503 ? 'Backend service unavailable' : 'Unknown error',
          status: response.status,
          request_id: requestId
        },
        { status: response.status }
      )
    }

    let data: any
    try {
      data = await response.json()
      console.log(`[${requestId}] Successfully processed query, response length: ${JSON.stringify(data).length} chars`)
    } catch (parseError) {
      console.error(`[${requestId}] Failed to parse successful response:`, parseError)
      return NextResponse.json(
        { 
          error: 'Invalid response from backend API',
          details: 'Failed to parse JSON response',
          request_id: requestId
        },
        { status: 500 }
      )
    }

    // Ensure response has required fields with defaults
    const enhancedData = {
      answer_bn: data.answer_bn || '',
      answer_en: data.answer_en || undefined,
      sources: Array.isArray(data.sources) ? data.sources : [],
      flags: {
        disagreement: Boolean(data.flags?.disagreement),
        single_source: Boolean(data.flags?.single_source),
        ...data.flags
      },
      metrics: {
        source_count: Number(data.metrics?.source_count) || 0,
        updated_ct: data.metrics?.updated_ct || new Date().toISOString(),
        latency_ms: data.metrics?.latency_ms,
        intent: data.metrics?.intent,
        confidence: data.metrics?.confidence,
        request_id: requestId,
        ...data.metrics
      },
      followups: Array.isArray(data.followups) ? data.followups : []
    }
    
    // Add anti-cache headers to response
    return new NextResponse(JSON.stringify(enhancedData), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache, no-store, must-revalidate, proxy-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        'X-Request-ID': requestId,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    })

  } catch (error) {
    const requestId = crypto.randomUUID()
    console.error(`[${requestId}] API Route Error:`, error)
    
    return NextResponse.json(
      { 
        error: 'Internal server error',
        message: error instanceof Error ? error.message : 'Unknown error',
        request_id: requestId
      },
      { 
        status: 500,
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'X-Request-ID': requestId,
        }
      }
    )
  }
}

// Handle preflight requests
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  })
}