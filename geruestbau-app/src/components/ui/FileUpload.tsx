import { useCallback, useState } from 'react'
import { Upload, FileText, X, Loader2, Camera, File, PenLine } from 'lucide-react'

interface FileUploadProps {
  onFileSelect: (file: File) => void
  accept?: string
  loading?: boolean
  disabled?: boolean
  selectedFile?: File | null
  onClear?: () => void
}

export default function FileUpload({
  onFileSelect,
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
          {/* Clear button nur wenn nicht loading */}
          {!loading && onClear && (
            <button
              type="button"
              onClick={onClear}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
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
    <div>
      {/* Unified drop zone - handles files and camera on mobile */}
      <label
        className={`
          relative block border-2 border-dashed rounded-2xl p-8 text-center transition-all
          ${isDragging ? 'border-primary-500 bg-primary-50 scale-[1.01]' : 'border-gray-300 hover:border-gray-400'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="flex flex-col items-center gap-4">
          {/* Upload cloud icon */}
          <div className="w-12 h-12 flex items-center justify-center">
            <Upload className="w-8 h-8 text-gray-400" />
          </div>

          {/* Main text */}
          <div>
            <p className="text-lg font-semibold text-gray-800">
              Datei hier ablegen oder klicken
            </p>
            <p className="text-sm text-gray-400 mt-1">
              PDF, JPG, PNG, HEIC (max. 10 MB)
            </p>
          </div>

          {/* Supported types icons */}
          <div className="flex items-center gap-4 mt-2">
            <div className="flex items-center gap-1.5 text-gray-400">
              <Camera className="w-4 h-4" />
              <span className="text-xs">Foto</span>
            </div>
            <div className="flex items-center gap-1.5 text-gray-400">
              <File className="w-4 h-4" />
              <span className="text-xs">PDF</span>
            </div>
            <div className="flex items-center gap-1.5 text-gray-400">
              <PenLine className="w-4 h-4" />
              <span className="text-xs">Skizze</span>
            </div>
          </div>
        </div>

        {/* Hidden file input - handles both file selection and camera on mobile */}
        <input
          type="file"
          accept={accept}
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={disabled}
        />
      </label>
    </div>
  )
}
