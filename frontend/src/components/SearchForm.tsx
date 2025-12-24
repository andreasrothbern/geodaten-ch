import { useState, useEffect } from 'react'

interface SearchFormProps {
  onSearch: (address: string) => void
  loading: boolean
  defaultAddress?: string
}

export function SearchForm({ onSearch, loading, defaultAddress }: SearchFormProps) {
  const [address, setAddress] = useState(defaultAddress || '')

  // Update address when defaultAddress changes (e.g., from URL parameter)
  useEffect(() => {
    if (defaultAddress) {
      setAddress(defaultAddress)
    }
  }, [defaultAddress])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (address.trim()) {
      onSearch(address.trim())
    }
  }

  const examples = [
    'Bundesplatz 3, 3011 Bern',
    'Kramgasse 10, Bern',
    'Bahnhofstrasse 1, Zürich',
  ]

  return (
    <form onSubmit={handleSubmit}>
      <div className="flex gap-3">
        <input
          type="text"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="Adresse eingeben..."
          className="input flex-1"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !address.trim()}
          className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              Suche...
            </span>
          ) : (
            'Suchen'
          )}
        </button>
      </div>

      {/* Quick Examples */}
      <div className="mt-3 flex flex-wrap gap-2">
        <span className="text-sm text-gray-500">Beispiele:</span>
        {examples.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => setAddress(example)}
            className="text-sm text-red-600 hover:underline"
          >
            {example}
          </button>
        ))}
      </div>
    </form>
  )
}
