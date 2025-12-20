import { useState, useEffect } from 'react'

interface ApiStatusProps {
  apiUrl: string
}

export function ApiStatus({ apiUrl }: ApiStatusProps) {
  const [status, setStatus] = useState<'checking' | 'online' | 'offline'>('checking')

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch(`${apiUrl}/health`)
        setStatus(response.ok ? 'online' : 'offline')
      } catch {
        setStatus('offline')
      }
    }

    checkHealth()
    const interval = setInterval(checkHealth, 30000) // Alle 30 Sekunden

    return () => clearInterval(interval)
  }, [apiUrl])

  if (status === 'checking') {
    return null
  }

  return (
    <div className="mb-4 flex items-center gap-2 text-sm">
      <span
        className={`w-2 h-2 rounded-full ${
          status === 'online' ? 'bg-green-500' : 'bg-red-500'
        }`}
      />
      <span className={status === 'online' ? 'text-green-700' : 'text-red-700'}>
        API: {status === 'online' ? 'Online' : 'Offline'}
      </span>
    </div>
  )
}
