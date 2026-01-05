import { Check } from 'lucide-react'

interface Step {
  id: number
  label: string
}

interface StepIndicatorProps {
  steps: Step[]
  currentStep: number
  isComplete?: boolean  // Letzter Step erfolgreich abgeschlossen
}

export default function StepIndicator({ steps, currentStep, isComplete }: StepIndicatorProps) {
  return (
    <div className="flex items-center justify-center gap-2 mb-6">
      {steps.map((step, index) => {
        const isLastStep = index === steps.length - 1
        const isStepComplete = step.id < currentStep || (isLastStep && isComplete)

        return (
        <div key={step.id} className="flex items-center">
          {/* Step Circle */}
          <div
            className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium transition-colors ${
              isStepComplete
                ? 'bg-green-600 text-white'
                : step.id === currentStep
                ? 'bg-primary-600 text-white ring-2 ring-primary-300'
                : 'bg-gray-200 text-gray-500'
            }`}
          >
            {isStepComplete ? (
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
                isStepComplete ? 'bg-green-600' : 'bg-gray-200'
              }`}
            />
          )}
        </div>
        )
      })}
    </div>
  )
}
