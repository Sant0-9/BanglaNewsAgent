/**
 * @jest-environment jsdom
 */

import { render, screen } from '@testing-library/react'
import { ConfidenceIndicator } from '../confidence-indicator'

describe('ConfidenceIndicator', () => {
  it('should not render for high confidence by default', () => {
    render(<ConfidenceIndicator confidence={0.8} />)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('should render for low confidence (< 0.6)', () => {
    render(<ConfidenceIndicator confidence={0.5} />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByText(/50%/)).toBeInTheDocument()
  })

  it('should render for very low confidence (< 0.4)', () => {
    render(<ConfidenceIndicator confidence={0.3} />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByText(/30%/)).toBeInTheDocument()
  })

  it('should show different variants based on confidence level', () => {
    // Very low confidence
    render(<ConfidenceIndicator confidence={0.2} />)
    const veryLowElement = screen.getByRole('status')
    expect(veryLowElement).toHaveClass('bg-red-500/10', 'text-red-600')
    
    // Low confidence
    render(<ConfidenceIndicator confidence={0.5} />)
    const lowElement = screen.getAllByRole('status')[1]
    expect(lowElement).toHaveClass('bg-amber-500/10', 'text-amber-600')
  })

  it('should render for high confidence when showAlways is true', () => {
    render(<ConfidenceIndicator confidence={0.9} showAlways />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByText(/90%/)).toBeInTheDocument()
  })

  it('should not render when confidence is undefined', () => {
    render(<ConfidenceIndicator />)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('should apply correct accessibility attributes', () => {
    render(<ConfidenceIndicator confidence={0.4} />)
    
    const indicator = screen.getByRole('status')
    expect(indicator).toHaveAttribute('aria-label', 'Low confidence: 40%')
    expect(indicator).toHaveAttribute('title', 'Low Confidence: 40% confidence in this response')
  })

  it('should display short label on mobile and full label on desktop', () => {
    render(<ConfidenceIndicator confidence={0.3} />)
    
    // Short label should be visible on mobile (without sm: prefix)
    expect(screen.getByText('30%')).toBeInTheDocument()
    
    // Full label should be hidden on mobile (with sm: prefix)
    const hiddenElement = document.querySelector('.hidden.sm\\:inline')
    expect(hiddenElement).toHaveTextContent('Low confidence')
  })

  it('should apply custom className', () => {
    render(<ConfidenceIndicator confidence={0.4} className="custom-class" />)
    
    const indicator = screen.getByRole('status')
    expect(indicator).toHaveClass('custom-class')
  })

  it('should use correct icons for different confidence levels', () => {
    // Very low and low use AlertTriangle, medium uses Info
    render(<ConfidenceIndicator confidence={0.3} />)
    expect(document.querySelector('svg')).toBeInTheDocument()
  })

  it('should round confidence percentage correctly', () => {
    render(<ConfidenceIndicator confidence={0.456} />)
    expect(screen.getByText('46%')).toBeInTheDocument()
    
    render(<ConfidenceIndicator confidence={0.555} />)
    expect(screen.getAllByText('56%')[0]).toBeInTheDocument()
  })
})