import { useCallback, useState } from 'react'
import { Upload, Camera, FileText, X, Loader2 } from 'lucide-react'

interface FileUploadProps {
  onFileSelect: (file: File) => void
  onCameraCapture?: () => void
  accept?: string
  loading?: boolean
  disabled?: boolean
  selectedFile?: File | null
  onClear?: () => void
}

export default function FileUpload({
  onFileSelect,
  onCameraCapture,
  accept = '.pdf,image/*',
  loading = false,
  disabled = false,
  selectedFile,
  onClear,
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)

      const file = e.dataTransfer.files[0]
      if (file && !disabled) {
        onFileSelect(file)
      }
    },
    [onFileSelect, disabled]
  )

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) {
        onFileSelect(file)
      }
    },
    [onFileSelect]
  )

  const getFileIcon = (file: File) => {
    if (file.type === 'application/pdf') {
      return <FileText className="w-8 h-8 text-red-500" />
    }
    return <FileText className="w-8 h-8 text-blue-500" />
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // Show selected file
  if (selectedFile) {
    return (
      <div className="border-2 border-primary-200 bg-primary-50 rounded-xl p-4">
        <div className="flex items-center gap-3">
          {getFileIcon(selectedFile)}
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-900 truncate">
              {selectedFile.name}
            </p>
            <p className="text-sm text-gray-500">
              {formatFileSize(selectedFile.size)}
            </p>
          </div>
          {loading ? (
            <Loader2 className="w-5 h-5 text-primary-600 animate-spin" />
          ) : (
            onClear && (
              <button
                type="button"
                onClick={onClear}
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            )
          )}
        </div>
        {loading && (
          <div className="mt-3 text-sm text-primary-600 flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Dokument wird analysiert...
          </div>
        )}
      </div>
    )
  }

  return (
    <div
      className={`
        border-2 border-dashed rounded-xl p-6 text-center transition-colors
        ${isDragging ? 'border-primary-500 bg-primary-50' : 'border-gray-300'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="flex flex-col items-center gap-3">
        <div className="p-3 bg-gray-100 rounded-full">
          <Upload className="w-6 h-6 text-gray-500" />
        </div>

        <div>
          <p className="text-gray-700 font-medium">
            PDF hier ablegen oder klicken zum Upload
          </p>
          <p className="text-sm text-gray-500 mt-1">
            PDF, JPG, PNG (max. 10 MB)
          </p>
        </div>

        <input
          type="file"
          accept={accept}
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={disabled}
          style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 }}
        />
      </div>

      {/* Divider with "oder" */}
      <div className="relative my-4">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-200" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-white px-3 text-sm text-gray-500">oder</span>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 justify-center">
        {onCameraCapture && (
          <button
            type="button"
            onClick={onCameraCapture}
            disabled={disabled}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200
                       rounded-lg text-gray-700 font-medium transition-colors disabled:opacity-50"
          >
            <Camera className="w-5 h-5" />
            Foto aufnehmen
          </button>
        )}

        <label
          className={`
            flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200
            rounded-lg text-gray-700 font-medium transition-colors cursor-pointer
            ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          <FileText className="w-5 h-5" />
          Datei wählen
          <input
            type="file"
            accept={accept}
            onChange={handleFileInput}
            className="hidden"
            disabled={disabled}
          />
        </label>
      </div>
    </div>
  )
}
