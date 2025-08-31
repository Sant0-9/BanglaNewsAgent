/**
 * @jest-environment jsdom
 */

import { renderHook, act } from '@testing-library/react'
import { useLoadingSystem } from '../use-loading-system'

// Mock timers for testing
jest.useFakeTimers()

describe('useLoadingSystem', () => {
  beforeEach(() => {
    jest.clearAllTimers()
  })

  afterEach(() => {
    act(() => {
      jest.runOnlyPendingTimers()
    })
  })

  it('should initialize with idle state', () => {
    const { result } = renderHook(() => useLoadingSystem())
    
    expect(result.current.state).toBe('idle')
    expect(result.current.isThinkingVisible).toBe(false)
    expect(result.current.isGeneratingVisible).toBe(false)
    expect(result.current.currentPhase).toBe(0)
    expect(result.current.showLongRunningHint).toBe(false)
    expect(result.current.realPhaseEvents).toEqual([])
    expect(result.current.timeElapsed).toBe(0)
  })

  it('should transition to thinking state when startThinking is called', () => {
    const { result } = renderHook(() => useLoadingSystem())
    
    act(() => {
      result.current.actions.startThinking()
    })
    
    expect(result.current.state).toBe('thinking')
    expect(result.current.isThinkingVisible).toBe(true)
    expect(result.current.isGeneratingVisible).toBe(false)
    expect(result.current.showLongRunningHint).toBe(false)
  })

  it('should transition to generating state when startGenerating is called', () => {
    const { result } = renderHook(() => useLoadingSystem())
    
    act(() => {
      result.current.actions.startThinking()
    })
    
    act(() => {
      result.current.actions.startGenerating()
    })
    
    expect(result.current.state).toBe('generating')
    expect(result.current.isThinkingVisible).toBe(false)
    expect(result.current.isGeneratingVisible).toBe(true)
  })

  it('should return to idle state when stop is called', () => {
    const { result } = renderHook(() => useLoadingSystem())
    
    act(() => {
      result.current.actions.startThinking()
    })
    
    act(() => {
      result.current.actions.stop()
    })
    
    expect(result.current.state).toBe('idle')
    expect(result.current.isThinkingVisible).toBe(false)
    expect(result.current.isGeneratingVisible).toBe(false)
    expect(result.current.currentPhase).toBe(0)
  })

  it('should handle cancel correctly', () => {
    const { result } = renderHook(() => useLoadingSystem())
    
    act(() => {
      result.current.actions.startThinking()
    })
    
    act(() => {
      result.current.actions.cancel()
    })
    
    expect(result.current.state).toBe('idle')
    expect(result.current.isThinkingVisible).toBe(false)
    expect(result.current.isGeneratingVisible).toBe(false)
  })

  it('should reset all state when reset is called', () => {
    const { result } = renderHook(() => useLoadingSystem())
    
    // Set up some state
    act(() => {
      result.current.actions.startThinking()
      result.current.actions.addPhaseEvent('fetching')
    })
    
    act(() => {
      result.current.actions.reset()
    })
    
    expect(result.current.state).toBe('idle')
    expect(result.current.currentPhase).toBe(0)
    expect(result.current.realPhaseEvents).toEqual([])
    expect(result.current.timeElapsed).toBe(0)
  })

  it('should add phase events correctly', () => {
    const { result } = renderHook(() => useLoadingSystem())
    
    act(() => {
      result.current.actions.addPhaseEvent('fetching')
    })
    
    expect(result.current.realPhaseEvents).toEqual(['fetching'])
    
    act(() => {
      result.current.actions.addPhaseEvent('deduping')
    })
    
    expect(result.current.realPhaseEvents).toEqual(['fetching', 'deduping'])
  })

  it('should limit phase events to last 4', () => {
    const { result } = renderHook(() => useLoadingSystem())
    
    act(() => {
      result.current.actions.addPhaseEvent('fetching')
      result.current.actions.addPhaseEvent('deduping')
      result.current.actions.addPhaseEvent('reranking')
      result.current.actions.addPhaseEvent('summarizing')
      result.current.actions.addPhaseEvent('fetching') // This should push out the first one
    })
    
    expect(result.current.realPhaseEvents).toEqual([
      'deduping', 'reranking', 'summarizing', 'fetching'
    ])
    expect(result.current.realPhaseEvents.length).toBe(4)
  })

  it('should call onStateChange callback when state changes', () => {
    const mockOnStateChange = jest.fn()
    const { result } = renderHook(() => 
      useLoadingSystem({ onStateChange: mockOnStateChange })
    )
    
    act(() => {
      result.current.actions.startThinking()
    })
    
    expect(mockOnStateChange).toHaveBeenCalledWith('thinking')
    
    act(() => {
      result.current.actions.startGenerating()
    })
    
    expect(mockOnStateChange).toHaveBeenCalledWith('generating')
    
    act(() => {
      result.current.actions.stop()
    })
    
    expect(mockOnStateChange).toHaveBeenCalledWith('idle')
  })

  it('should call onPhaseChange callback when phase changes', () => {
    const mockOnPhaseChange = jest.fn()
    const { result } = renderHook(() => 
      useLoadingSystem({ onPhaseChange: mockOnPhaseChange })
    )
    
    act(() => {
      result.current.onPhaseChange(2)
    })
    
    expect(mockOnPhaseChange).toHaveBeenCalledWith(2)
  })

  it('should show long running hint after threshold', () => {
    const { result } = renderHook(() => 
      useLoadingSystem({ longRunningThreshold: 1000 })
    )
    
    act(() => {
      result.current.actions.startThinking()
    })
    
    expect(result.current.showLongRunningHint).toBe(false)
    
    // Fast-forward time past the threshold
    act(() => {
      jest.advanceTimersByTime(1001)
    })
    
    expect(result.current.showLongRunningHint).toBe(true)
  })

  it('should clear long running hint when state changes', () => {
    const { result } = renderHook(() => 
      useLoadingSystem({ longRunningThreshold: 1000 })
    )
    
    act(() => {
      result.current.actions.startThinking()
    })
    
    act(() => {
      jest.advanceTimersByTime(1001)
    })
    
    expect(result.current.showLongRunningHint).toBe(true)
    
    act(() => {
      result.current.actions.startGenerating()
    })
    
    expect(result.current.showLongRunningHint).toBe(false)
  })

  it('should update elapsed time during operation', () => {
    const mockDateNow = jest.spyOn(Date, 'now')
    let currentTime = 1000
    mockDateNow.mockImplementation(() => currentTime)

    const { result } = renderHook(() => useLoadingSystem())
    
    act(() => {
      result.current.actions.startThinking()
    })
    
    expect(result.current.timeElapsed).toBe(0)
    
    // Simulate time passing
    currentTime += 500
    act(() => {
      jest.advanceTimersByTime(100) // Advance the timer interval
    })
    
    expect(result.current.timeElapsed).toBe(500)
    
    mockDateNow.mockRestore()
  })

  it('should use correct mode', () => {
    const { result } = renderHook(() => 
      useLoadingSystem({ mode: 'sports' })
    )
    
    expect(result.current.mode).toBe('sports')
  })

  it('should cleanup timers on unmount', () => {
    const { result, unmount } = renderHook(() => useLoadingSystem())
    
    act(() => {
      result.current.actions.startThinking()
    })
    
    const clearTimeoutSpy = jest.spyOn(global, 'clearTimeout')
    const clearIntervalSpy = jest.spyOn(global, 'clearInterval')
    
    unmount()
    
    expect(clearTimeoutSpy).toHaveBeenCalled()
    expect(clearIntervalSpy).toHaveBeenCalled()
    
    clearTimeoutSpy.mockRestore()
    clearIntervalSpy.mockRestore()
  })

  it('should handle multiple state transitions correctly', () => {
    const mockOnStateChange = jest.fn()
    const { result } = renderHook(() => 
      useLoadingSystem({ onStateChange: mockOnStateChange })
    )
    
    // Start thinking
    act(() => {
      result.current.actions.startThinking()
    })
    expect(result.current.state).toBe('thinking')
    
    // Move to generating
    act(() => {
      result.current.actions.startGenerating()
    })
    expect(result.current.state).toBe('generating')
    
    // Stop
    act(() => {
      result.current.actions.stop()
    })
    expect(result.current.state).toBe('idle')
    
    // Verify all state changes were reported
    expect(mockOnStateChange).toHaveBeenNthCalledWith(1, 'thinking')
    expect(mockOnStateChange).toHaveBeenNthCalledWith(2, 'generating')
    expect(mockOnStateChange).toHaveBeenNthCalledWith(3, 'idle')
  })
})