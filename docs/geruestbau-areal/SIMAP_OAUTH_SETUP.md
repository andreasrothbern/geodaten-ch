# simap.ch OAuth/OIDC Setup für Gerüstbau-App

## 1. Direktlink zu Gerüstbau-Ausschreibungen

**Aktuelle Gerüstbau-Ausschreibungen auf simap.ch:**

```
https://www.simap.ch/de/search?q=Ger%C3%BCst&cpvCodes=45262100-2
```

Oder direkt mit CPV-Code für Gerüstarbeiten:
- `45262100-2` - Gerüstarbeiten (Hauptcode)
- `45262110-5` - Abbau von Gerüsten
- `45262120-8` - Aufbau von Gerüsten

---

## 2. API-Registrierung

### Registrierungsformular (M2M-Zugang)

**URL:** https://forms.office.com/pages/responsepage.aspx?id=o2w6IQhIR0CKyoFNLN5EdGFhHlNcfO1OgKkZv7DGPcRUOExMVldHSlpKVFZHMk5YOVRXU1g0VzlWSS4u

### API-Dokumentation

| Umgebung | URL |
|----------|-----|
| **Test/Integration** | https://int.simap.ch/api-doc |
| **Produktion** | https://www.simap.ch/api-doc |

---

## 3. OAuth/OIDC Konfiguration für unser Projekt

simap.ch verwendet **OpenID Connect** mit 2FA. Bei der Registrierung muss man `redirectUri` und `webOrigins` angeben.

### ✅ Registrierte Werte (Stand: 31.12.2024)

#### redirectUri (bei simap.ch hinterlegt)

```
https://geruestbau.railway.app/auth/callback
https://acceptable-trust-production.up.railway.app/auth/callback
```

#### webOrigins (bei simap.ch hinterlegt)

```
https://geruestbau.railway.app
https://acceptable-trust-production.up.railway.app
```

### Erklärung der URLs

| URL | Verwendung |
|-----|------------|
| `geruestbau.railway.app` | Custom Domain (falls konfiguriert) |
| `acceptable-trust-production.up.railway.app` | Railway-generierte Domain |

### Lokale Entwicklung

Für lokales Testen müssten noch hinzugefügt werden:

```
http://localhost:3001/auth/callback
http://localhost:5173/auth/callback
```

**Hinweis:** simap.ch erlaubt möglicherweise keine `http://` URLs. In dem Fall:
- Lokal mit Production-Token testen, oder
- ngrok/cloudflare tunnel für HTTPS verwenden

---

## 4. Implementierung im Frontend

### Auth Callback Route

```tsx
// geruestbau-app/src/pages/AuthCallbackPage.tsx

import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Loader2 } from 'lucide-react'

export function AuthCallbackPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  
  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')
    const errorParam = searchParams.get('error')
    
    if (errorParam) {
      setError(`Authentifizierung fehlgeschlagen: ${errorParam}`)
      return
    }
    
    if (code) {
      // Token austauschen
      exchangeCodeForToken(code, state)
        .then(() => {
          // Zurück zur ursprünglichen Seite
          const returnUrl = sessionStorage.getItem('simap_return_url') || '/projects'
          sessionStorage.removeItem('simap_return_url')
          navigate(returnUrl)
        })
        .catch(err => {
          setError(err.message)
        })
    }
  }, [searchParams, navigate])
  
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <button onClick={() => navigate('/')} className="btn-primary">
            Zurück zur Startseite
          </button>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary-600" />
        <p className="text-gray-600">Anmeldung wird verarbeitet...</p>
      </div>
    </div>
  )
}

async function exchangeCodeForToken(code: string, state: string | null) {
  const response = await fetch('/api/v1/geruestbau/auth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, state }),
  })
  
  if (!response.ok) {
    throw new Error('Token-Austausch fehlgeschlagen')
  }
  
  const data = await response.json()
  
  // Token im localStorage speichern
  localStorage.setItem('simap_access_token', data.access_token)
  if (data.refresh_token) {
    localStorage.setItem('simap_refresh_token', data.refresh_token)
  }
  
  return data
}
```

### Router-Konfiguration

```tsx
// geruestbau-app/src/App.tsx

import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthCallbackPage } from './pages/AuthCallbackPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* ... andere Routes ... */}
        
        {/* OAuth Callback Routes */}
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route path="/simap/callback" element={<AuthCallbackPage />} />
      </Routes>
    </BrowserRouter>
  )
}
```

---

## 5. Backend OAuth Flow

### backend/app/routers/auth.py

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
import httpx
import os
from urllib.parse import urlencode

router = APIRouter(prefix="/auth", tags=["auth"])

# simap.ch OIDC Endpoints
SIMAP_AUTH_URL = "https://www.simap.ch/auth/realms/simap/protocol/openid-connect/auth"
SIMAP_TOKEN_URL = "https://www.simap.ch/auth/realms/simap/protocol/openid-connect/token"

# Aus Umgebungsvariablen
CLIENT_ID = os.getenv("SIMAP_CLIENT_ID", "geruestbau-app")
CLIENT_SECRET = os.getenv("SIMAP_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("SIMAP_REDIRECT_URI", "http://localhost:3001/auth/callback")


@router.get("/login")
async def login_redirect(return_url: str = "/projects"):
    """
    Leitet zur simap.ch Login-Seite weiter.
    """
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": REDIRECT_URI,
        "state": return_url,  # Speichere return URL im state
    }
    
    auth_url = f"{SIMAP_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.post("/token")
async def exchange_token(code: str, state: str = None):
    """
    Tauscht Authorization Code gegen Access Token.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            SIMAP_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Token-Austausch fehlgeschlagen: {response.text}"
            )
        
        return response.json()


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """
    Erneuert Access Token mit Refresh Token.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            SIMAP_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Token-Erneuerung fehlgeschlagen")
        
        return response.json()
```

---

## 6. Umgebungsvariablen

### Railway Environment (Produktion)

```bash
# simap.ch OAuth
SIMAP_CLIENT_ID=<wird nach Registrierung mitgeteilt>
SIMAP_CLIENT_SECRET=<wird nach Registrierung mitgeteilt>
SIMAP_REDIRECT_URI=https://geruestbau.railway.app/auth/callback
SIMAP_AUTH_URL=https://www.simap.ch/auth/realms/simap/protocol/openid-connect/auth
SIMAP_TOKEN_URL=https://www.simap.ch/auth/realms/simap/protocol/openid-connect/token
```

### Alternative Railway Domain

Falls `geruestbau.railway.app` nicht verfügbar:
```bash
SIMAP_REDIRECT_URI=https://acceptable-trust-production.up.railway.app/auth/callback
```

---

## 7. Wichtige Hinweise

### 2FA-Einschränkung

simap.ch erfordert **2-Faktor-Authentifizierung per E-Mail** für jeden Login. Das bedeutet:

1. ❌ **Kein vollautomatischer M2M-Zugriff** möglich
2. ✅ **Nutzer muss sich manuell einloggen** (einmalig pro Session)
3. ✅ **Refresh Tokens** können Session verlängern

### Empfohlener User Flow

```
1. Nutzer klickt "Mit simap.ch verbinden"
2. → Weiterleitung zu simap.ch Login
3. → Nutzer gibt Username/Passwort ein
4. → Nutzer erhält E-Mail mit 2FA-Code
5. → Nutzer gibt 2FA-Code ein
6. → Callback zu unserer App mit Auth Code
7. → Backend tauscht Code gegen Token
8. → Nutzer kann simap.ch API nutzen
```

### Session-Dauer

- Access Token: ~5-15 Minuten (typisch)
- Refresh Token: ~8 Stunden (typisch)
- Nach Ablauf: Erneuter Login erforderlich

---

## 8. Alternative: Öffentliche API ohne Auth

Für **reine Lesezugriffe** auf Ausschreibungen ist **keine Authentifizierung** nötig:

```python
# Öffentliche Suche ohne Login
async def search_public_tenders(query: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.simap.ch/api/publications/v1/search",
            params={
                "q": query,
                "publicationType": "TENDER",
                "status": "PUBLISHED",
            }
        )
        return response.json()
```

**Was ohne Login geht:**
- ✅ Ausschreibungen suchen
- ✅ Publikationen lesen
- ✅ Grunddaten abrufen

**Was Login braucht:**
- ❌ Ausschreibungsunterlagen herunterladen
- ❌ Fragen im Forum stellen
- ❌ Interesse bekunden
- ❌ Angebote einreichen

---

## 9. Zusammenfassung Registrierung

### ✅ Bereits registriert (31.12.2024)

| Feld | Wert |
|------|------|
| **redirectUri** | `https://geruestbau.railway.app/auth/callback` |
| | `https://acceptable-trust-production.up.railway.app/auth/callback` |
| **webOrigins** | `https://geruestbau.railway.app` |
| | `https://acceptable-trust-production.up.railway.app` |

### Warten auf

- Client-ID und Client-Secret von simap.ch
- Bestätigung der Registrierung

### Workflow bis dahin

1. **Öffentliche API nutzen** - Ausschreibungen suchen, Daten extrahieren
2. **Manueller Dokumenten-Download** - User loggt sich auf simap.ch ein
3. **Dokumente in App hochladen** - Zu Projekt-Files hinzufügen

---

*Stand: Dezember 2024*
