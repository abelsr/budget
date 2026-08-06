import { useEffect, useState } from "react"

import { apiFetchBlob } from "@/lib/api"

interface ProfileAvatarProps {
  name: string
  hasAvatar: boolean
  avatarUpdatedAt: string | null
  className?: string
}

/** Avatar privado: la imagen se lee autenticada y nunca se expone en una URL pública. */
export function ProfileAvatar({
  name,
  hasAvatar,
  avatarUpdatedAt,
  className = "",
}: ProfileAvatarProps) {
  const [source, setSource] = useState<string | null>(null)
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "?"

  useEffect(() => {
    let active = true
    let objectUrl: string | null = null
    setSource(null)

    if (!hasAvatar) return

    apiFetchBlob("/auth/me/avatar")
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob)
        if (active) setSource(objectUrl)
        else URL.revokeObjectURL(objectUrl)
      })
      .catch(() => {
        // El fallback con iniciales conserva la interfaz si la lectura falla.
      })

    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [hasAvatar, avatarUpdatedAt])

  if (source) {
    return <img src={source} alt={`Avatar de ${name}`} className={`object-cover ${className}`} />
  }

  return (
    <span
      role="img"
      aria-label={`Iniciales de ${name}`}
      className={`flex items-center justify-center ${className}`}
    >
      {initials}
    </span>
  )
}
