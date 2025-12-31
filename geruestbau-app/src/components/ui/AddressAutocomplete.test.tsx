import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import AddressAutocomplete from './AddressAutocomplete'

// Mock swisstopo API response
const mockSwisstopoResponse = {
  results: [
    {
      attrs: {
        label: '<b>Bundesplatz</b> 3, 3011 Bern',
        detail: 'Bern BE',
        lat: 46.9466,
        lon: 7.4448,
        x: 2600450,
        y: 1199830,
        featureId: 'addr_123',
      },
    },
    {
      attrs: {
        label: '<b>Bundesplatz</b> 5, 3011 Bern',
        detail: 'Bern BE',
        lat: 46.9467,
        lon: 7.4449,
        x: 2600460,
        y: 1199840,
        featureId: 'addr_124',
      },
    },
  ],
}

describe('AddressAutocomplete', () => {
  const mockOnChange = vi.fn()
  const mockOnSelect = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    // Use real timers for most tests, mock fetch instead
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders input field', () => {
    render(<AddressAutocomplete value="" onChange={mockOnChange} />)
    expect(screen.getByPlaceholderText('Strasse Nr, PLZ Ort')).toBeInTheDocument()
  })

  it('renders with custom placeholder', () => {
    render(
      <AddressAutocomplete
        value=""
        onChange={mockOnChange}
        placeholder="Custom placeholder"
      />
    )
    expect(screen.getByPlaceholderText('Custom placeholder')).toBeInTheDocument()
  })

  it('calls onChange when typing', async () => {
    render(<AddressAutocomplete value="" onChange={mockOnChange} />)
    const input = screen.getByPlaceholderText('Strasse Nr, PLZ Ort')

    fireEvent.change(input, { target: { value: 'Bund' } })
    expect(mockOnChange).toHaveBeenCalledWith('Bund')
  })

  it('does not search with less than 3 characters', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSwisstopoResponse),
    })
    global.fetch = fetchMock

    render(<AddressAutocomplete value="Bu" onChange={mockOnChange} />)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    expect(fetchMock).not.toHaveBeenCalled()
    vi.useRealTimers()
  })

  it('searches after 3 characters with debounce', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSwisstopoResponse),
    })
    global.fetch = fetchMock

    const { rerender } = render(
      <AddressAutocomplete value="" onChange={mockOnChange} />
    )

    // Simulate typing "Bun"
    rerender(<AddressAutocomplete value="Bun" onChange={mockOnChange} />)

    // Should not call immediately
    expect(fetchMock).not.toHaveBeenCalled()

    // After debounce delay
    await act(async () => {
      await vi.advanceTimersByTimeAsync(350)
    })
    expect(fetchMock).toHaveBeenCalled()

    // Check correct URL
    const callUrl = fetchMock.mock.calls[0][0] as string
    expect(callUrl).toContain('api3.geo.admin.ch')
    expect(callUrl).toContain('searchText=Bun')
    expect(callUrl).toContain('type=locations')
    expect(callUrl).toContain('origins=address')
    vi.useRealTimers()
  })

  it('displays suggestions from API', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSwisstopoResponse),
    })
    global.fetch = fetchMock

    render(<AddressAutocomplete value="Bundesplatz" onChange={mockOnChange} />)

    // Wait for debounce and API call
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled()
    }, { timeout: 1000 })

    await waitFor(() => {
      expect(screen.getByText('Bundesplatz 3, 3011 Bern')).toBeInTheDocument()
      expect(screen.getByText('Bundesplatz 5, 3011 Bern')).toBeInTheDocument()
    })
  })

  it('calls onSelect when clicking suggestion', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSwisstopoResponse),
    })
    global.fetch = fetchMock

    render(
      <AddressAutocomplete
        value="Bundesplatz"
        onChange={mockOnChange}
        onSelect={mockOnSelect}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Bundesplatz 3, 3011 Bern')).toBeInTheDocument()
    }, { timeout: 1000 })

    fireEvent.click(screen.getByText('Bundesplatz 3, 3011 Bern'))

    expect(mockOnChange).toHaveBeenCalledWith('Bundesplatz 3, 3011 Bern')
    expect(mockOnSelect).toHaveBeenCalledWith(
      expect.objectContaining({
        label: 'Bundesplatz 3, 3011 Bern',
        lat: 46.9466,
        lon: 7.4448,
      })
    )
  })

  it('shows no results message when API returns empty', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: [] }),
    })
    global.fetch = fetchMock

    render(<AddressAutocomplete value="xyz123" onChange={mockOnChange} />)

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled()
    }, { timeout: 1000 })

    await waitFor(() => {
      expect(screen.getByText('Keine Adresse gefunden')).toBeInTheDocument()
    })
  })

  it('clears input when clicking X button', async () => {
    render(<AddressAutocomplete value="Test" onChange={mockOnChange} />)

    const clearButton = screen.getByRole('button')
    fireEvent.click(clearButton)

    expect(mockOnChange).toHaveBeenCalledWith('')
  })

  it('supports keyboard navigation', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSwisstopoResponse),
    })
    global.fetch = fetchMock

    render(
      <AddressAutocomplete
        value="Bundesplatz"
        onChange={mockOnChange}
        onSelect={mockOnSelect}
      />
    )

    const input = screen.getByPlaceholderText('Strasse Nr, PLZ Ort')

    await waitFor(() => {
      expect(screen.getByText('Bundesplatz 3, 3011 Bern')).toBeInTheDocument()
    }, { timeout: 1000 })

    // Arrow down should highlight first item
    fireEvent.keyDown(input, { key: 'ArrowDown' })

    // Arrow down again should highlight second item
    fireEvent.keyDown(input, { key: 'ArrowDown' })

    // Enter should select highlighted item
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(mockOnChange).toHaveBeenCalledWith('Bundesplatz 5, 3011 Bern')
  })

  it('closes dropdown on Escape', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSwisstopoResponse),
    })
    global.fetch = fetchMock

    render(<AddressAutocomplete value="Bundesplatz" onChange={mockOnChange} />)

    const input = screen.getByPlaceholderText('Strasse Nr, PLZ Ort')

    await waitFor(() => {
      expect(screen.getByText('Bundesplatz 3, 3011 Bern')).toBeInTheDocument()
    }, { timeout: 1000 })

    fireEvent.keyDown(input, { key: 'Escape' })

    await waitFor(() => {
      expect(screen.queryByText('Bundesplatz 3, 3011 Bern')).not.toBeInTheDocument()
    })
  })

  it('is disabled when disabled prop is true', () => {
    render(
      <AddressAutocomplete value="" onChange={mockOnChange} disabled={true} />
    )
    const input = screen.getByPlaceholderText('Strasse Nr, PLZ Ort')
    expect(input).toBeDisabled()
  })
})
