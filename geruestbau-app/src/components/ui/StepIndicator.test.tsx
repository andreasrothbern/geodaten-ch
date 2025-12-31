import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import StepIndicator from './StepIndicator'

const mockSteps = [
  { id: 1, label: 'Import' },
  { id: 2, label: 'Prüfen' },
  { id: 3, label: 'Geodaten' },
]

describe('StepIndicator', () => {
  it('renders all steps', () => {
    render(<StepIndicator steps={mockSteps} currentStep={1} />)

    expect(screen.getByText('Import')).toBeInTheDocument()
    expect(screen.getByText('Prüfen')).toBeInTheDocument()
    expect(screen.getByText('Geodaten')).toBeInTheDocument()
  })

  it('shows step numbers for pending steps', () => {
    render(<StepIndicator steps={mockSteps} currentStep={1} />)

    // Step 1 is current, steps 2 and 3 should show numbers
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('shows checkmark for completed steps', () => {
    render(<StepIndicator steps={mockSteps} currentStep={3} />)

    // Steps 1 and 2 are completed, should have checkmarks (SVG icons)
    // We can check that step numbers 1 and 2 are not visible
    expect(screen.queryByText('1')).not.toBeInTheDocument()
    expect(screen.queryByText('2')).not.toBeInTheDocument()
    // Step 3 is current, should still show number
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('applies active styles to current step', () => {
    const { container } = render(
      <StepIndicator steps={mockSteps} currentStep={2} />
    )

    // The step circles have different styles based on state
    const stepCircles = container.querySelectorAll('.rounded-full')
    expect(stepCircles).toHaveLength(3)

    // Step 1 should be completed (bg-primary-600)
    expect(stepCircles[0]).toHaveClass('bg-primary-600')
    // Step 2 should be current (bg-primary-600 with ring)
    expect(stepCircles[1]).toHaveClass('bg-primary-600')
    expect(stepCircles[1]).toHaveClass('ring-2')
    // Step 3 should be pending (bg-gray-200)
    expect(stepCircles[2]).toHaveClass('bg-gray-200')
  })

  it('renders connector lines between steps', () => {
    const { container } = render(
      <StepIndicator steps={mockSteps} currentStep={2} />
    )

    // Should have 2 connector lines (between 3 steps)
    const connectors = container.querySelectorAll('.h-0\\.5')
    expect(connectors).toHaveLength(2)

    // First connector should be completed (bg-primary-600)
    expect(connectors[0]).toHaveClass('bg-primary-600')
    // Second connector should be pending (bg-gray-200)
    expect(connectors[1]).toHaveClass('bg-gray-200')
  })

  it('handles single step', () => {
    const singleStep = [{ id: 1, label: 'Only Step' }]
    render(<StepIndicator steps={singleStep} currentStep={1} />)

    expect(screen.getByText('Only Step')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
  })

  it('handles two steps', () => {
    const twoSteps = [
      { id: 1, label: 'First' },
      { id: 2, label: 'Second' },
    ]
    const { container } = render(
      <StepIndicator steps={twoSteps} currentStep={1} />
    )

    expect(screen.getByText('First')).toBeInTheDocument()
    expect(screen.getByText('Second')).toBeInTheDocument()

    // Should have 1 connector line
    const connectors = container.querySelectorAll('.h-0\\.5')
    expect(connectors).toHaveLength(1)
  })

  it('shows all steps as completed when on last step', () => {
    render(<StepIndicator steps={mockSteps} currentStep={3} />)

    // Steps 1 and 2 completed, step 3 is current
    // Check that the first two steps don't show their numbers
    expect(screen.queryByText('1')).not.toBeInTheDocument()
    expect(screen.queryByText('2')).not.toBeInTheDocument()
    // Step 3 is current
    expect(screen.getByText('3')).toBeInTheDocument()
  })
})
