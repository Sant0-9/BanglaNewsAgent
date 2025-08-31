/**
 * @jest-environment jsdom
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { CitationSystem } from '../citation-system'
import type { Source } from '../../lib/types'

// Mock framer-motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

// Mock the hook
jest.mock('../../hooks/use-citation-system', () => ({
  useCitationSystem: () => ({
    highlightedSources: new Set(),
    highlightedMarkers: new Set(),
    currentMarkerIndex: -1,
    containerRef: { current: null },
    handleMarkerClick: jest.fn(),
    handleSourceClick: jest.fn(),
    scrollToSource: jest.fn(),
    scrollToMarker: jest.fn(),
    navigateMarkers: jest.fn(),
    clearHighlights: jest.fn(),
    totalSources: 2,
    hasKeyboardNavigation: true
  })
}))

const mockSources: Source[] = [
  {
    name: "BBC News",
    url: "https://www.bbc.com/news/article-1",
    published_at: "2024-01-01T10:00:00Z",
    logo: "https://example.com/bbc-logo.png"
  },
  {
    name: "CNN",
    url: "https://www.cnn.com/news/article-2",
    published_at: "2024-01-01T11:00:00Z"
  }
]

describe('CitationSystem', () => {
  const defaultProps = {
    sources: mockSources,
    content: "This is a test message with citations.",
    messageId: "test-message-123"
  }

  it('should render message content with inline markers', () => {
    render(<CitationSystem {...defaultProps} />)
    
    expect(screen.getByText("This is a test message with citations.")).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Source reference 1/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Source reference 2/i })).toBeInTheDocument()
  })

  it('should render sources tray when sources are provided', () => {
    render(<CitationSystem {...defaultProps} />)
    
    expect(screen.getByText('Sources')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument() // Source count
  })

  it('should show confidence indicator for low confidence', () => {
    render(<CitationSystem {...defaultProps} confidence={0.4} />)
    
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByText(/40%/)).toBeInTheDocument()
  })

  it('should not show confidence indicator for high confidence by default', () => {
    render(<CitationSystem {...defaultProps} confidence={0.8} />)
    
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('should show confidence indicator always when showConfidenceAlways is true', () => {
    render(<CitationSystem {...defaultProps} confidence={0.8} showConfidenceAlways />)
    
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByText(/80%/)).toBeInTheDocument()
  })

  it('should render keyboard navigation hint when enabled', () => {
    render(<CitationSystem {...defaultProps} enableKeyboardNavigation />)
    
    expect(screen.getByText(/use/i)).toBeInTheDocument()
    expect(screen.getByText('[')).toBeInTheDocument()
    expect(screen.getByText(']')).toBeInTheDocument()
  })

  it('should not render content when no sources provided', () => {
    render(<CitationSystem {...defaultProps} sources={[]} />)
    
    expect(screen.queryByText('Sources')).not.toBeInTheDocument()
  })

  it('should handle empty content gracefully', () => {
    render(<CitationSystem {...defaultProps} content="" />)
    
    expect(screen.getByText('Sources')).toBeInTheDocument()
  })

  it('should apply correct ARIA attributes for keyboard navigation', () => {
    render(<CitationSystem {...defaultProps} enableKeyboardNavigation />)
    
    const container = screen.getByRole('region')
    expect(container).toHaveAttribute('aria-label', 'Message with citations - use [ and ] to navigate')
    expect(container).toHaveAttribute('tabIndex', '0')
  })

  it('should not apply ARIA region when keyboard navigation is disabled', () => {
    render(<CitationSystem {...defaultProps} enableKeyboardNavigation={false} />)
    
    expect(screen.queryByRole('region')).not.toBeInTheDocument()
  })

  it('should use provided messageId as data attribute', () => {
    render(<CitationSystem {...defaultProps} messageId="custom-message-id" />)
    
    const container = document.querySelector('[data-message-id="custom-message-id"]')
    expect(container).toBeInTheDocument()
  })

  it('should handle missing optional props', () => {
    const minimalProps = {
      sources: mockSources,
      content: "Test content"
    }
    
    expect(() => render(<CitationSystem {...minimalProps} />)).not.toThrow()
  })

  it('should insert markers in logical positions within content', () => {
    const longContent = "This is the first sentence. This is the second sentence. This is the third sentence."
    render(<CitationSystem {...defaultProps} content={longContent} />)
    
    // Should have markers distributed throughout the content
    expect(screen.getByRole('button', { name: /Source reference 1/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Source reference 2/i })).toBeInTheDocument()
  })
})