import { useState, useEffect, useRef, useCallback } from 'react'
import { MapPin, Loader2, X } from 'lucide-react'

interface AddressSuggestion {
  label: string
  detail: string
  lat: number
  lon: number
  // Original swisstopo data
  attrs: {
    label: string
    detail: string
    lat: number
    lon: number
    x: number  // LV95 E
    y: number  // LV95 N
    featureId: string
  }
}

interface AddressAutocompleteProps {
  value: string
  onChange: (value: string) => void
  onSelect?: (suggestion: AddressSuggestion) => void
  placeholder?: string
  disabled?: boolean
  className?: string
  required?: boolean
}

// swisstopo API base URL
const SWISSTOPO_API = 'https://api3.geo.admin.ch/rest/services/api/SearchServer'

// Debounce delay in ms
const DEBOUNCE_DELAY = 300

// Minimum characters before searching
const MIN_CHARS = 3

export default function AddressAutocomplete({
  value,
  onChange,
  onSelect,
  placeholder = 'Strasse Nr, PLZ Ort',
  disabled = false,
  className = '',
  required = false,
}: AddressAutocompleteProps) {
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isOpen, setIsOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Fetch suggestions from swisstopo
  const fetchSuggestions = useCallback(async (searchText: string) => {
    if (searchText.length < MIN_CHARS) {
      setSuggestions([])
      return
    }

    setIsLoading(true)

    try {
      const params = new URLSearchParams({
        searchText: searchText,
        type: 'locations',
        origins: 'address',
        limit: '8',
      })

      const response = await fetch(`${SWISSTOPO_API}?${params}`)
      if (!response.ok) throw new Error('API error')

      const data = await response.json()

      // Map swisstopo results to our format
      const mapped: AddressSuggestion[] = (data.results || []).map((result: any) => ({
        label: result.attrs.label.replace(/<[^>]*>/g, ''),  // Remove HTML tags
        detail: result.attrs.detail || '',
        lat: result.attrs.lat,
        lon: result.attrs.lon,
        attrs: result.attrs,
      }))

      setSuggestions(mapped)
      setIsOpen(mapped.length > 0)
      setHighlightedIndex(-1)
    } catch (error) {
      console.error('Address search error:', error)
      setSuggestions([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    if (value.length >= MIN_CHARS) {
      debounceRef.current = setTimeout(() => {
        fetchSuggestions(value)
      }, DEBOUNCE_DELAY)
    } else {
      setSuggestions([])
      setIsOpen(false)
    }

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [value, fetchSuggestions])

  // Handle suggestion selection
  const handleSelect = useCallback(
    (suggestion: AddressSuggestion) => {
      onChange(suggestion.label)
      setSuggestions([])
      setIsOpen(false)
      onSelect?.(suggestion)
      inputRef.current?.blur()
    },
    [onChange, onSelect]
  )

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!isOpen || suggestions.length === 0) return

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setHighlightedIndex((prev) =>
            prev < suggestions.length - 1 ? prev + 1 : 0
          )
          break
        case 'ArrowUp':
          e.preventDefault()
          setHighlightedIndex((prev) =>
            prev > 0 ? prev - 1 : suggestions.length - 1
          )
          break
        case 'Enter':
          e.preventDefault()
          if (highlightedIndex >= 0 && highlightedIndex < suggestions.length) {
            handleSelect(suggestions[highlightedIndex])
          }
          break
        case 'Escape':
          setIsOpen(false)
          setHighlightedIndex(-1)
          break
      }
    },
    [isOpen, suggestions, highlightedIndex, handleSelect]
  )

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const item = listRef.current.children[highlightedIndex] as HTMLElement
      if (item) {
        item.scrollIntoView({ block: 'nearest' })
      }
    }
  }, [highlightedIndex])

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        inputRef.current &&
        !inputRef.current.contains(e.target as Node) &&
        listRef.current &&
        !listRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className="relative">
      {/* Input */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          className={`input-field pr-10 ${className}`}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => suggestions.length > 0 && setIsOpen(true)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          required={required}
          autoComplete="off"
        />

        {/* Icons */}
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {isLoading && (
            <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
          )}
          {value && !isLoading && (
            <button
              type="button"
              onClick={() => {
                onChange('')
                setSuggestions([])
                inputRef.current?.focus()
              }}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Suggestions Dropdown */}
      {isOpen && suggestions.length > 0 && (
        <ul
          ref={listRef}
          className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-auto"
        >
          {suggestions.map((suggestion, index) => (
            <li
              key={`${suggestion.attrs.featureId}-${index}`}
              className={`px-3 py-2 cursor-pointer flex items-start gap-2 ${
                index === highlightedIndex
                  ? 'bg-primary-50 text-primary-900'
                  : 'hover:bg-gray-50'
              }`}
              onClick={() => handleSelect(suggestion)}
              onMouseEnter={() => setHighlightedIndex(index)}
            >
              <MapPin className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
              <div className="min-w-0">
                <div className="text-sm font-medium truncate">
                  {suggestion.label}
                </div>
                {suggestion.detail && (
                  <div className="text-xs text-gray-500 truncate">
                    {suggestion.detail}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* No results message */}
      {isOpen && !isLoading && value.length >= MIN_CHARS && suggestions.length === 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm text-gray-500">
          Keine Adresse gefunden
        </div>
      )}
    </div>
  )
}
