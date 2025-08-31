/**
 * @jest-environment jsdom
 */

import { render, screen, waitFor } from '@testing-library/react'
import { ThinkingOverlay } from '../thinking-overlay'

// Mock framer-motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

// Mock the child components
jest.mock('../aura-pulse', () => ({
  AuraPulse: ({ mode }: { mode: string }) => <div data-testid="aura-pulse" data-mode={mode} />,
}))

jest.mock('../particle-halo', () => ({
  ParticleHalo: ({ mode }: { mode: string }) => <div data-testid="particle-halo" data-mode={mode} />,
}))

jest.mock('../thinking-steps', () => ({
  ThinkingSteps: ({ mode, onPhaseChange }: { mode: string; onPhaseChange?: (phase: number) => void }) => (
    <div data-testid="thinking-steps" data-mode={mode}>
      <button onClick={() => onPhaseChange?.(1)}>Change Phase</button>
    </div>
  ),
}))

describe('ThinkingOverlay', () => {
  afterEach(() => {
    // Reset body styles
    document.body.style.pointerEvents = ''
  })

  it('should render when visible', () => {
    render(<ThinkingOverlay isVisible={true} />)
    
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByLabelText('Preparing response')).toBeInTheDocument()
  })

  it('should not render when not visible', () => {
    render(<ThinkingOverlay isVisible={false} />)
    
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('should render with correct mode', () => {
    render(<ThinkingOverlay isVisible={true} mode="sports" />)
    
    expect(screen.getByTestId('aura-pulse')).toHaveAttribute('data-mode', 'sports')
    expect(screen.getByTestId('particle-halo')).toHaveAttribute('data-mode', 'sports')
    expect(screen.getByTestId('thinking-steps')).toHaveAttribute('data-mode', 'sports')
  })

  it('should apply custom className', () => {
    render(<ThinkingOverlay isVisible={true} className="custom-class" />)
    
    const overlay = screen.getByRole('status')
    expect(overlay).toHaveClass('custom-class')
  })

  it('should disable body pointer events when visible', async () => {
    render(<ThinkingOverlay isVisible={true} />)
    
    await waitFor(() => {
      expect(document.body.style.pointerEvents).toBe('none')
    })
  })

  it('should restore body pointer events when not visible', async () => {
    const { rerender } = render(<ThinkingOverlay isVisible={true} />)
    
    await waitFor(() => {
      expect(document.body.style.pointerEvents).toBe('none')
    })

    rerender(<ThinkingOverlay isVisible={false} />)
    
    await waitFor(() => {
      expect(document.body.style.pointerEvents).toBe('')
    })
  })

  it('should call onPhaseChange when phase changes', () => {
    const mockOnPhaseChange = jest.fn()
    
    render(<ThinkingOverlay isVisible={true} onPhaseChange={mockOnPhaseChange} />)
    
    const button = screen.getByText('Change Phase')
    button.click()
    
    expect(mockOnPhaseChange).toHaveBeenCalledWith(1)
  })

  it('should have proper accessibility attributes', () => {
    render(<ThinkingOverlay isVisible={true} />)
    
    const overlay = screen.getByRole('status')
    expect(overlay).toHaveAttribute('aria-live', 'polite')
    expect(overlay).toHaveAttribute('aria-label', 'Preparing response')
  })

  it('should default to general mode', () => {
    render(<ThinkingOverlay isVisible={true} />)
    
    expect(screen.getByTestId('aura-pulse')).toHaveAttribute('data-mode', 'general')
    expect(screen.getByTestId('particle-halo')).toHaveAttribute('data-mode', 'general')
    expect(screen.getByTestId('thinking-steps')).toHaveAttribute('data-mode', 'general')
  })
})