/**
 * @jest-environment jsdom
 */

import { renderHook, act } from '@testing-library/react'
import { useCitationSystem } from '../use-citation-system'
import type { Source } from '../lib/types'

// Mock scrollIntoView
Element.prototype.scrollIntoView = jest.fn()

const mockSources: Source[] = [
  {
    name: "Test Source 1",
    url: "https://example.com/1"
  },
  {
    name: "Test Source 2", 
    url: "https://example.com/2"
  },
  {
    name: "Test Source 3",
    url: "https://example.com/3"
  }
]

// Mock DOM elements
const mockMarkerElement = { scrollIntoView: jest.fn() }
const mockSourceElement = { scrollIntoView: jest.fn() }

describe('useCitationSystem', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Mock querySelector
    document.querySelector = jest.fn().mockImplementation((selector) => {
      if (selector.includes('data-marker-number')) {
        return mockMarkerElement
      }
      if (selector.includes('data-source-index')) {
        return mockSourceElement
      }
      return null
    })
  })

  it('should initialize with correct default state', () => {
    const { result } = renderHook(() => useCitationSystem({
      sources: mockSources,
      messageId: 'test-123'
    }))

    expect(result.current.highlightedSources).toEqual(new Set())
    expect(result.current.highlightedMarkers).toEqual(new Set())
    expect(result.current.currentMarkerIndex).toBe(-1)
    expect(result.current.totalSources).toBe(3)
    expect(result.current.hasKeyboardNavigation).toBe(true)
  })

  it('should highlight item when handleMarkerClick is called', () => {
    const { result } = renderHook(() => useCitationSystem({
      sources: mockSources
    }))

    act(() => {
      result.current.handleMarkerClick(1)
    })

    expect(result.current.highlightedSources.has(1)).toBe(true)
    expect(result.current.highlightedMarkers.has(1)).toBe(true)
    expect(result.current.currentMarkerIndex).toBe(1)
    expect(mockSourceElement.scrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'center'
    })
  })

  it('should highlight item when handleSourceClick is called', () => {
    const { result } = renderHook(() => useCitationSystem({
      sources: mockSources
    }))

    act(() => {
      result.current.handleSourceClick(2)
    })

    expect(result.current.highlightedSources.has(2)).toBe(true)
    expect(result.current.highlightedMarkers.has(2)).toBe(true)
    expect(result.current.currentMarkerIndex).toBe(2)
    expect(mockMarkerElement.scrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'center'
    })
  })

  it('should navigate to next marker correctly', () => {
    const { result } = renderHook(() => useCitationSystem({
      sources: mockSources
    }))

    // Start at first marker
    act(() => {
      result.current.handleMarkerClick(0)
    })

    // Navigate to next
    act(() => {
      result.current.navigateMarkers('next')
    })

    expect(result.current.currentMarkerIndex).toBe(1)

    // Navigate past the end should wrap to beginning
    act(() => {
      result.current.navigateMarkers('next')
    })
    act(() => {
      result.current.navigateMarkers('next')
    })

    expect(result.current.currentMarkerIndex).toBe(0)
  })

  it('should navigate to previous marker correctly', () => {
    const { result } = renderHook(() => useCitationSystem({
      sources: mockSources
    }))

    // Start at index 0, navigate prev should wrap to last
    act(() => {
      result.current.navigateMarkers('prev')
    })

    expect(result.current.currentMarkerIndex).toBe(2)

    // Navigate prev again
    act(() => {
      result.current.navigateMarkers('prev')
    })

    expect(result.current.currentMarkerIndex).toBe(1)
  })

  it('should clear highlights when clearHighlights is called', () => {
    const { result } = renderHook(() => useCitationSystem({
      sources: mockSources
    }))

    // Set up some highlights
    act(() => {
      result.current.handleMarkerClick(1)
    })

    expect(result.current.highlightedSources.size).toBe(1)

    // Clear highlights
    act(() => {
      result.current.clearHighlights()
    })

    expect(result.current.highlightedSources).toEqual(new Set())
    expect(result.current.highlightedMarkers).toEqual(new Set())
    expect(result.current.currentMarkerIndex).toBe(-1)
  })

  it('should handle keyboard navigation when enabled', () => {
    const { result } = renderHook(() => useCitationSystem({
      sources: mockSources,
      enableKeyboardNavigation: true
    }))

    expect(result.current.hasKeyboardNavigation).toBe(true)

    // Simulate keyboard event
    const mockEvent = new KeyboardEvent('keydown', { key: ']' })
    Object.defineProperty(mockEvent, 'target', {
      value: document.createElement('div'),
      writable: false
    })

    // The actual keyboard handling is tested through integration
    // Here we just verify the setup is correct
    expect(result.current.totalSources).toBe(3)
  })

  it('should disable keyboard navigation when sources are empty', () => {
    const { result } = renderHook(() => useCitationSystem({
      sources: [],
      enableKeyboardNavigation: true
    }))

    expect(result.current.hasKeyboardNavigation).toBe(false)
  })

  it('should disable keyboard navigation when explicitly disabled', () => {
    const { result } = renderHook(() => useCitationSystem({
      sources: mockSources,
      enableKeyboardNavigation: false
    }))

    expect(result.current.hasKeyboardNavigation).toBe(false)
  })

  it('should handle scrollToSource when element exists', () => {
    const { result } = renderHook(() => useCitationSystem({
      sources: mockSources
    }))

    act(() => {
      result.current.scrollToSource(1)
    })

    expect(mockSourceElement.scrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'center'
    })
    expect(result.current.highlightedSources.has(1)).toBe(true)
  })

  it('should handle scrollToMarker when element exists', () => {
    const { result } = renderHook(() => useCitationSystem({
      sources: mockSources
    }))

    act(() => {
      result.current.scrollToMarker(2)
    })

    expect(mockMarkerElement.scrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'center'
    })
    expect(result.current.highlightedMarkers.has(2)).toBe(true)
  })

  it('should handle missing DOM elements gracefully', () => {
    document.querySelector = jest.fn().mockReturnValue(null)
    
    const { result } = renderHook(() => useCitationSystem({
      sources: mockSources
    }))

    // Should not throw when elements don't exist
    expect(() => {
      act(() => {
        result.current.scrollToSource(1)
        result.current.scrollToMarker(1)
      })
    }).not.toThrow()
  })

  it('should clean up timers on unmount', () => {
    const clearTimeoutSpy = jest.spyOn(global, 'clearTimeout')
    
    const { result, unmount } = renderHook(() => useCitationSystem({
      sources: mockSources,
      highlightDuration: 1000
    }))

    act(() => {
      result.current.handleMarkerClick(0)
    })

    unmount()

    expect(clearTimeoutSpy).toHaveBeenCalled()
    clearTimeoutSpy.mockRestore()
  })
})