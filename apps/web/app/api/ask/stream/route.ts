import { NextRequest } from 'next/server'
import { API_BASE } from '../../../../lib/config'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // Validate request body
    if (!body.query || typeof body.query !== 'string') {
      return new Response(
        JSON.stringify({ error: 'Query is required and must be a string' }),
        { 
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        }
      )
    }

    // Check if backend supports streaming
    const streamEndpoint = `${API_BASE}/ask/stream`
    
    try {
      // Try streaming endpoint first
      const response = await fetch(streamEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // Do not forward arbitrary UI modes; backend defines its own defaults.
        body: JSON.stringify({
          query: body.query,
          lang: body.lang || 'bn'
        })
      })

      if (response.ok && response.body) {
        // Forward the streaming response
        return new Response(response.body, {
          status: 200,
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
          }
        })
      }
    } catch (streamError) {
      console.log('Streaming endpoint not available, falling back to regular endpoint')
    }

    // Fallback to regular endpoint with simulated streaming
    const fallbackResponse = await fetch(`${API_BASE}/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: body.query,
        lang: body.lang || 'bn'
      })
    })

    if (!fallbackResponse.ok) {
      const errorData = await fallbackResponse.text()
      console.error('API Error:', errorData)
      
      return new Response(
        `data: ${JSON.stringify({ 
          error: 'Backend API error',
          details: fallbackResponse.status === 404 ? 'API endpoint not found' : 'Unknown error'
        })}\n\n`,
        {
          status: 200,
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
          }
        }
      )
    }

    const data = await fallbackResponse.json()
    const content = data.answer_bn || data.answer_en || data.answer

    // Simulate streaming by chunking the response
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      async start(controller) {
        try {
          if (!content) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ 
              error: 'No content received from backend' 
            })}\n\n`))
            controller.enqueue(encoder.encode('data: [DONE]\n\n'))
            controller.close()
            return
          }

          // Split content into words for smooth streaming effect
          const words = content.split(' ')
          let currentChunk = ''
          
          for (let i = 0; i < words.length; i++) {
            currentChunk += (i > 0 ? ' ' : '') + words[i]
            
            // Send chunk every few words or at the end
            if (i % 3 === 0 || i === words.length - 1) {
              const chunkData = {
                content: i === words.length - 1 ? content : currentChunk,
                delta: words[i] + (i < words.length - 1 ? ' ' : ''),
                index: i,
                total: words.length,
                metadata: i === words.length - 1 ? {
                  intent: data.metrics?.intent,
                  confidence: data.metrics?.confidence,
                  sources: data.sources
                } : undefined
              }
              
              controller.enqueue(encoder.encode(`data: ${JSON.stringify(chunkData)}\n\n`))
              
              // Add small delay for realistic streaming feel
              if (i < words.length - 1) {
                await new Promise(resolve => setTimeout(resolve, 50))
              }
            }
          }
          
          // Send completion signal
          controller.enqueue(encoder.encode('data: [DONE]\n\n'))
          controller.close()
          
        } catch (error) {
          console.error('Stream error:', error)
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ 
            error: error instanceof Error ? error.message : 'Unknown streaming error' 
          })}\n\n`))
          controller.enqueue(encoder.encode('data: [DONE]\n\n'))
          controller.close()
        }
      }
    })

    return new Response(stream, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      }
    })

  } catch (error) {
    console.error('Streaming API Route Error:', error)
    
    const encoder = new TextEncoder()
    const errorStream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ 
          error: 'Internal server error',
          message: error instanceof Error ? error.message : 'Unknown error'
        })}\n\n`))
        controller.enqueue(encoder.encode('data: [DONE]\n\n'))
        controller.close()
      }
    })
    
    return new Response(errorStream, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      }
    })
  }
}

// Handle preflight requests
export async function OPTIONS() {
  return new Response(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  })
}