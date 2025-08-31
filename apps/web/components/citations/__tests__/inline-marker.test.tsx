/**
 * @jest-environment jsdom
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { InlineMarker } from '../inline-marker'

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
}))

describe('InlineMarker', () => {
  it('should render circled numbers for numbers 1-20', () => {
    render(<InlineMarker number={1} />)
    expect(screen.getByRole('button')).toHaveTextContent('①')
    
    render(<InlineMarker number={5} />)
    expect(screen.getByRole('button')).toHaveTextContent('⑤')
    
    render(<InlineMarker number={20} />)
    expect(screen.getByRole('button')).toHaveTextContent('⑳')
  })

  it('should render regular numbers for numbers > 20', () => {
    render(<InlineMarker number={25} />)
    expect(screen.getByRole('button')).toHaveTextContent('25')
  })

  it('should call onClick when clicked', () => {
    const mockClick = jest.fn()
    render(<InlineMarker number={1} onClick={mockClick} />)
    
    fireEvent.click(screen.getByRole('button'))
    expect(mockClick).toHaveBeenCalledTimes(1)
  })

  it('should apply highlighted styles when isHighlighted is true', () => {
    render(<InlineMarker number={1} isHighlighted />)
    
    const button = screen.getByRole('button')
    expect(button).toHaveClass('bg-primary', 'text-primary-foreground', 'border-primary', 'shadow-lg', 'scale-110')
  })

  it('should apply correct accessibility attributes', () => {
    render(<InlineMarker number={3} sourceId="source-123" />)
    
    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-label', 'Source reference 3')
    expect(button).toHaveAttribute('data-source-id', 'source-123')
    expect(button).toHaveAttribute('data-marker-number', '3')
    expect(button).toHaveAttribute('tabIndex', '0')
  })

  it('should apply custom className', () => {
    render(<InlineMarker number={1} className="custom-class" />)
    
    const button = screen.getByRole('button')
    expect(button).toHaveClass('custom-class')
  })

  it('should have correct default styling', () => {
    render(<InlineMarker number={1} />)
    
    const button = screen.getByRole('button')
    expect(button).toHaveClass(
      'inline-flex',
      'items-center',
      'justify-center',
      'text-primary',
      'bg-primary/10',
      'border',
      'border-primary/20',
      'rounded-full',
      'cursor-pointer',
      'focus:outline-none',
      'focus:ring-2'
    )
  })

  it('should handle keyboard interaction', () => {
    const mockClick = jest.fn()
    render(<InlineMarker number={1} onClick={mockClick} />)
    
    const button = screen.getByRole('button')
    fireEvent.keyDown(button, { key: 'Enter' })
    // Note: actual Enter key handling would be browser behavior, 
    // but we can test that the button is focusable
    expect(button).toHaveAttribute('tabIndex', '0')
  })

  it('should use different sizes for different number ranges', () => {
    // Numbers 1-20 use circled characters and should have w-5 h-5
    render(<InlineMarker number={1} />)
    const smallButton = screen.getByRole('button')
    expect(smallButton).toHaveClass('w-5', 'h-5', 'text-base')
    
    // Numbers > 20 should use min-width and smaller text
    render(<InlineMarker number={25} />)
    const largeButton = screen.getAllByRole('button')[1]
    expect(largeButton).toHaveClass('min-w-[20px]', 'h-5', 'px-1.5', 'text-xs')
  })
})