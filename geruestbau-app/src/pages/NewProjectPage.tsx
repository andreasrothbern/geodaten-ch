import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { geruestbauApi } from '../api/geruestbau'

export default function NewProjectPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    name: '',
    address: '',
    client_name: '',
    description: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      const project = await geruestbauApi.createProject(form)
      // Automatisch Geodaten abrufen
      await geruestbauApi.enrichProject(project.id)
      navigate(`/projects/${project.id}`)
    } catch (error) {
      console.error('Fehler beim Erstellen:', error)
      alert('Fehler beim Erstellen des Projekts')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Projektname *
        </label>
        <input
          type="text"
          className="input-field"
          placeholder="z.B. Gerüst Kirche St. Peter"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Adresse *
        </label>
        <input
          type="text"
          className="input-field"
          placeholder="Strasse Nr, PLZ Ort"
          value={form.address}
          onChange={(e) => setForm({ ...form, address: e.target.value })}
          required
        />
        <p className="text-xs text-gray-500 mt-1">
          Geodaten werden automatisch von geodaten-ch abgerufen
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Auftraggeber
        </label>
        <input
          type="text"
          className="input-field"
          placeholder="Name / Firma"
          value={form.client_name}
          onChange={(e) => setForm({ ...form, client_name: e.target.value })}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Beschreibung
        </label>
        <textarea
          className="input-field min-h-[100px]"
          placeholder="Projektdetails..."
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
      </div>

      <button
        type="submit"
        className="btn-primary mt-6"
        disabled={loading || !form.name || !form.address}
      >
        {loading ? 'Wird erstellt...' : 'Projekt erstellen'}
      </button>
    </form>
  )
}
