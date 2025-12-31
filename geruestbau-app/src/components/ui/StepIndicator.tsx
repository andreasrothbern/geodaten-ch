import { Check } from 'lucide-react'

interface Step {
  id: number
  label: string
}

interface StepIndicatorProps {
  steps: Step[]
  currentStep: number
}

export default function StepIndicator({ steps, currentStep }: StepIndicatorProps) {
  return (
    <div className="flex items-center justify-center gap-2 mb-6">
      {steps.map((step, index) => (
        <div key={step.id} className="flex items-center">
          {/* Step Circle */}
          <div
            className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium transition-colors ${
              step.id < currentStep
                ? 'bg-primary-600 text-white'
                : step.id === currentStep
                ? 'bg-primary-600 text-white ring-2 ring-primary-300'
                : 'bg-gray-200 text-gray-500'
            }`}
          >
            {step.id < currentStep ? (
              <Check className="w-4 h-4" />
            ) : (
              step.id
            )}
          </div>

          {/* Step Label */}
          <span
            className={`ml-2 text-sm hidden sm:inline ${
              step.id <= currentStep
                ? 'text-gray-900 font-medium'
                : 'text-gray-500'
            }`}
          >
            {step.label}
          </span>

          {/* Connector Line */}
          {index < steps.length - 1 && (
            <div
              className={`w-8 sm:w-16 h-0.5 mx-2 sm:mx-4 ${
                step.id < currentStep ? 'bg-primary-600' : 'bg-gray-200'
              }`}
            />
          )}
        </div>
      ))}
    </div>
  )
}
