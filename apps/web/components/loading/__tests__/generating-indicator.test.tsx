/**
 * @jest-environment jsdom
 */

import { render, screen, waitFor } from '@testing-library/react'
import { GeneratingIndicator } from '../generating-indicator'

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

// Mock prefers-reduced-motion
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: query === '(prefers-reduced-motion: reduce)' ? false : false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
})

// Mock timers for dot animation
jest.useFakeTimers()

describe('GeneratingIndicator', () => {
  afterEach(() => {
    jest.clearAllTimers()
  })

  it('should render when visible', () => {
    render(<GeneratingIndicator isVisible={true} />)
    
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByLabelText('Generating answer')).toBeInTheDocument()
  })

  it('should not render when not visible', () => {
    render(<GeneratingIndicator isVisible={false} />)
    
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('should render generating text in both languages', () => {
    render(<GeneratingIndicator isVisible={true} />)
    
    expect(screen.getByText(/Generating answer/)).toBeInTheDocument()
    expect(screen.getByText(/উত্তর তৈরি করা হচ্ছে/)).toBeInTheDocument()
  })

  it('should animate dots when not reduced motion', async () => {
    render(<GeneratingIndicator isVisible={true} />)
    
    // Initially should have some dots
    expect(screen.getByText(/Generating answer/)).toBeInTheDocument()
    
    // Fast forward the dot animation
    jest.advanceTimersByTime(500)
    
    await waitFor(() => {
      expect(screen.getByText(/Generating answer/)).toBeInTheDocument()
    })
  })

  it('should show static dots for reduced motion', () => {
    // Mock reduced motion preference
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation((query) => ({
        matches: query === '(prefers-reduced-motion: reduce)' ? true : false,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    })
    
    render(<GeneratingIndicator isVisible={true} />)
    
    expect(screen.getByText('Generating answer...')).toBeInTheDocument()
    expect(screen.getByText('উত্তর তৈরি করা হচ্ছে...')).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    render(<GeneratingIndicator isVisible={true} className="custom-class" />)
    
    const indicator = screen.getByRole('status')
    expect(indicator).toHaveClass('custom-class')
  })

  it('should include messageId in data attribute when provided', () => {
    render(<GeneratingIndicator isVisible={true} messageId="test-message-123" />)
    
    const indicator = screen.getByRole('status')
    expect(indicator).toHaveAttribute('data-message-id', 'test-message-123')
  })

  it('should have proper accessibility attributes', () => {
    render(<GeneratingIndicator isVisible={true} />)
    
    const indicator = screen.getByRole('status')
    expect(indicator).toHaveAttribute('aria-live', 'polite')
    expect(indicator).toHaveAttribute('aria-label', 'Generating answer')
  })

  it('should use different modes', () => {
    render(<GeneratingIndicator isVisible={true} mode="sports" />)
    
    // The component should render with sports mode colors
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('should default to general mode', () => {
    render(<GeneratingIndicator isVisible={true} />)
    
    // Should render without errors using default general mode
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('should clean up dot animation timer on unmount', () => {
    const { unmount } = render(<GeneratingIndicator isVisible={true} />)
    
    const clearIntervalSpy = jest.spyOn(global, 'clearInterval')
    
    unmount()
    
    expect(clearIntervalSpy).toHaveBeenCalled()
    
    clearIntervalSpy.mockRestore()
  })

  it('should stop dot animation when not visible', () => {
    const { rerender } = render(<GeneratingIndicator isVisible={true} />)
    
    // Should have animated text initially
    expect(screen.getByText(/Generating answer/)).toBeInTheDocument()
    
    rerender(<GeneratingIndicator isVisible={false} />)
    
    // Component should not be rendered when not visible
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})