import { useEffect, useMemo, useState } from 'react'
import QRCode from 'react-qr-code'
import {
  ApiError,
  createBox,
  deleteBox,
  getBoxImageUrl,
  getLanIpv4,
  listBoxes,
  searchBoxes,
  updateBox,
  uploadBoxVideo,
  webappUrlForLanHost,
  type BoxResponse,
  type SearchHit,
} from './api'

const THEME_KEY = 'boxbrain-theme'
type Theme = 'light' | 'dark'

function getInitialTheme(): Theme {
  try {
    const s = localStorage.getItem(THEME_KEY)
    if (s === 'light' || s === 'dark') return s
  } catch {
    /* ignore */
  }
  if (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: light)').matches) {
    return 'light'
  }
  return 'dark'
}

type Tab = 'boxes' | 'search'

type PhoneQrState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ok'; url: string }
  | { status: 'error'; message: string }

function formatBoxSubtitle(box: BoxResponse) {
  const parts: string[] = []
  if (box.location) parts.push(box.location)
  parts.push(box.has_video ? 'scanned' : 'not scanned')
  return parts.join(' • ')
}

function App() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme)
  const [showPhoneQr, setShowPhoneQr] = useState(false)
  const [tab, setTab] = useState<Tab>('boxes')
  const [boxes, setBoxes] = useState<BoxResponse[] | null>(null)
  const [boxesError, setBoxesError] = useState<string | null>(null)
  const [boxesLoading, setBoxesLoading] = useState(false)

  const [selectedBoxId, setSelectedBoxId] = useState<number | null>(null)
  const [phoneQr, setPhoneQr] = useState<PhoneQrState>({ status: 'idle' })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    try {
      localStorage.setItem(THEME_KEY, theme)
    } catch {
      /* ignore */
    }
  }, [theme])

  const selectedBox = useMemo(
    () => boxes?.find((b) => b.id === selectedBoxId) ?? null,
    [boxes, selectedBoxId],
  )

  useEffect(() => {
    if (!showPhoneQr) {
      setPhoneQr({ status: 'idle' })
      return
    }
    let cancelled = false
    setPhoneQr({ status: 'loading' })
    ;(async () => {
      try {
        const ip = await getLanIpv4()
        if (cancelled) return
        if (!ip) {
          setPhoneQr({
            status: 'error',
            message:
              'Could not detect this computer’s LAN address. Check Wi‑Fi/ethernet, then try again.',
          })
          return
        }
        setPhoneQr({ status: 'ok', url: webappUrlForLanHost(ip) })
      } catch {
        if (!cancelled) {
          setPhoneQr({
            status: 'error',
            message:
              'Could not reach the API to detect the LAN address. Is the backend running (port 8000)?',
          })
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [showPhoneQr])

  async function refreshBoxes() {
    setBoxesError(null)
    setBoxesLoading(true)
    try {
      const data = await listBoxes()
      setBoxes(data)
      if (data.length > 0 && selectedBoxId == null) setSelectedBoxId(data[0].id)
    } catch (e) {
      setBoxesError(e instanceof Error ? e.message : 'Failed to load boxes')
    } finally {
      setBoxesLoading(false)
    }
  }

  useEffect(() => {
    void refreshBoxes()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar__row">
          <div className="topbar__title">BoxBrain</div>
          <div className="topbar__actions">
            <button
              type="button"
              className="qr-link-toggle"
              onClick={() => setShowPhoneQr((v) => !v)}
              aria-expanded={showPhoneQr}
              aria-controls="phone-qr-panel"
              title={
                showPhoneQr
                  ? 'Hide QR code for opening this app on your phone'
                  : 'Show QR code — opens this app using this computer’s LAN address'
              }
            >
              {showPhoneQr ? 'Hide QR' : 'Phone QR'}
            </button>
            <button
              type="button"
              className="theme-toggle"
              onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
          </div>
        </div>
        {showPhoneQr ? (
          <div
            id="phone-qr-panel"
            className="qr-panel"
            role="region"
            aria-label="Open BoxBrain on your phone"
          >
            {phoneQr.status !== 'ok' && phoneQr.status !== 'error' ? (
              <div className="muted">Detecting this computer’s LAN address…</div>
            ) : null}
            {phoneQr.status === 'error' ? <div className="alert alert--error">{phoneQr.message}</div> : null}
            {phoneQr.status === 'ok' ? (
              <>
                <p className="qr-panel__hint">
                  Scan on the same Wi‑Fi. The link uses this machine’s LAN IP and the same port as this
                  page (e.g. <span className="mono">:5173</span> for Vite).
                </p>
                <div className="qr-panel__code">
                  <QRCode value={phoneQr.url} size={200} level="M" bgColor="#ffffff" fgColor="#000000" />
                </div>
                <div className="qr-panel__url mono" title={phoneQr.url}>
                  {phoneQr.url}
                </div>
              </>
            ) : null}
          </div>
        ) : null}
        <div className="topbar__tabs" role="tablist" aria-label="Primary">
          <button
            type="button"
            className={tab === 'boxes' ? 'tab tab--active' : 'tab'}
            onClick={() => setTab('boxes')}
            role="tab"
            aria-selected={tab === 'boxes'}
          >
            Boxes
          </button>
          <button
            type="button"
            className={tab === 'search' ? 'tab tab--active' : 'tab'}
            onClick={() => setTab('search')}
            role="tab"
            aria-selected={tab === 'search'}
          >
            Search
          </button>
        </div>
      </header>

      <main className="content">
        {tab === 'boxes' ? (
          <BoxesScreen
            boxes={boxes}
            boxesError={boxesError}
            boxesLoading={boxesLoading}
            selectedBoxId={selectedBoxId}
            onSelectBox={(id) => setSelectedBoxId(id)}
            onRefresh={refreshBoxes}
            selectedBox={selectedBox}
          />
        ) : (
          <SearchScreen
            boxes={boxes ?? []}
            onSelectBox={(id) => {
              setSelectedBoxId(id)
              setTab('boxes')
            }}
          />
        )}
      </main>
    </div>
  )
}

function BoxesScreen(props: {
  boxes: BoxResponse[] | null
  boxesError: string | null
  boxesLoading: boolean
  selectedBoxId: number | null
  selectedBox: BoxResponse | null
  onSelectBox: (id: number | null) => void
  onRefresh: () => Promise<void>
}) {
  const { boxes, boxesError, boxesLoading, selectedBoxId, onSelectBox, onRefresh, selectedBox } = props

  const [createLabel, setCreateLabel] = useState('')
  const [createLocation, setCreateLocation] = useState('')
  const [createError, setCreateError] = useState<string | null>(null)
  const [createLoading, setCreateLoading] = useState(false)

  async function onCreate(e: React.FormEvent) {
    e.preventDefault()
    setCreateError(null)
    setCreateLoading(true)
    try {
      const box = await createBox({
        label: createLabel.trim(),
        location: createLocation.trim() || null,
      })
      setCreateLabel('')
      setCreateLocation('')
      await onRefresh()
      onSelectBox(box.id)
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setCreateError('That label is already used. Pick another.')
      } else {
        setCreateError(err instanceof Error ? err.message : 'Failed to create box')
      }
    } finally {
      setCreateLoading(false)
    }
  }

  return (
    <div className="stack">
      <section className="card">
        <div className="card__title">New box</div>
        <div className="card__subtitle">
          Label the physical box, then scan a 5–10s video of the open box. No item lists.
        </div>
        <form className="form" onSubmit={onCreate}>
          <label className="field">
            <div className="field__label">Box label</div>
            <input
              className="input"
              value={createLabel}
              onChange={(e) => setCreateLabel(e.target.value)}
              placeholder="e.g. attic_1"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              required
            />
          </label>
          <label className="field">
            <div className="field__label">Location (optional)</div>
            <input
              className="input"
              value={createLocation}
              onChange={(e) => setCreateLocation(e.target.value)}
              placeholder="e.g. garage shelf"
            />
          </label>
          {createError ? <div className="alert alert--error">{createError}</div> : null}
          <button className="button button--primary" type="submit" disabled={createLoading}>
            {createLoading ? 'Creating…' : 'Create box'}
          </button>
        </form>
      </section>

      <section className="card">
        <div className="row row--space">
          <div>
            <div className="card__title">Your boxes</div>
            <div className="card__subtitle">
              Tap a box to upload a scan video or update its location.
            </div>
          </div>
          <button className="button button--ghost" type="button" onClick={() => void onRefresh()}>
            Refresh
          </button>
        </div>

        {boxesError ? <div className="alert alert--error">{boxesError}</div> : null}
        {boxesLoading && boxes == null ? <div className="muted">Loading…</div> : null}
        {boxes && boxes.length === 0 ? (
          <div className="muted">No boxes yet. Create one above.</div>
        ) : null}

        {boxes && boxes.length > 0 ? (
          <div className="list">
            {boxes.map((box) => (
              <button
                key={box.id}
                type="button"
                className={box.id === selectedBoxId ? 'listItem listItem--active' : 'listItem'}
                onClick={() => onSelectBox(box.id)}
              >
                <div className="listItem__title">{box.label}</div>
                <div className="listItem__subtitle">{formatBoxSubtitle(box)}</div>
              </button>
            ))}
          </div>
        ) : null}
      </section>

      {selectedBox ? (
        <BoxDetailCard
          key={selectedBox.id}
          box={selectedBox}
          onRefresh={onRefresh}
          onDeleted={() => onSelectBox(null)}
        />
      ) : null}
    </div>
  )
}

function BoxDetailCard(props: {
  box: BoxResponse
  onRefresh: () => Promise<void>
  onDeleted: () => void
}) {
  const { box, onRefresh, onDeleted } = props
  const [location, setLocation] = useState(box.location ?? '')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  async function onSaveLocation(e: React.FormEvent) {
    e.preventDefault()
    setSaveError(null)
    setSaving(true)
    try {
      await updateBox(box.id, { location: location.trim() || null })
      await onRefresh()
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to update')
    } finally {
      setSaving(false)
    }
  }

  async function onUploadVideo(e: React.FormEvent) {
    e.preventDefault()
    if (!videoFile) return
    setUploadError(null)
    setUploading(true)
    try {
      await uploadBoxVideo(box.id, videoFile)
      setVideoFile(null)
      await onRefresh()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      const isAbort = err instanceof Error && err.name === 'AbortError'
      const isNetworkError =
        msg === 'Load failed' ||
        msg === 'Failed to fetch' ||
        msg.toLowerCase().includes('network')
      setUploadError(
        isAbort
          ? 'Upload timed out. Try a shorter video (5–10 seconds) or try again.'
          : isNetworkError
            ? 'Upload failed. Backend may be unreachable or the request timed out. Ensure the server is running (e.g. scripts/start.sh).'
            : msg
      )
    } finally {
      setUploading(false)
    }
  }

  return (
    <section className="card">
      <div className="card__title">Selected box</div>
      <div className="card__subtitle">
        <span className="mono">#{box.id}</span> • <span className="mono">{box.label}</span> •{' '}
        {box.has_video ? 'Scanned' : 'Not scanned yet'}
      </div>

      {box.has_video ? (
        <div className="box-image-wrap">
          <img
            src={getBoxImageUrl(box.id)}
            alt={`Scan of ${box.label}`}
            className="box-image"
          />
        </div>
      ) : null}

      {box.diagnostics ? (
        <div className="diagnostics">
          <div className="field__label">Capture quality</div>
          <ul className="diagnostics__list">
            <li><strong>Frames</strong>: {box.diagnostics.frame_count}</li>
            <li><strong>Brightness</strong>: {(box.diagnostics.brightness * 100).toFixed(0)}%</li>
            <li><strong>Sharpness</strong>: {box.diagnostics.blur_score.toFixed(1)} (higher = sharper)</li>
          </ul>
        </div>
      ) : null}

      {box.contents && box.contents.length > 0 ? (
        <div className="box-contents">
          <div className="field__label">Items in this box</div>
          <ul className="box-contents__list">
            {box.contents.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      ) : box.has_video ? (
        <div className="muted">No items detected yet.</div>
      ) : null}

      <form className="form" onSubmit={onSaveLocation}>
        <label className="field">
          <div className="field__label">Location</div>
          <input
            className="input"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. garage shelf"
          />
        </label>
        {saveError ? <div className="alert alert--error">{saveError}</div> : null}
        <button className="button" type="submit" disabled={saving}>
          {saving ? 'Saving…' : 'Save location'}
        </button>
      </form>

      <div className="divider" />

      <form className="form" onSubmit={onUploadVideo}>
        <div className="field">
          <div className="field__label">Scan video (5–10 seconds)</div>
          <span className="input--file-wrap">
            <input
              id={`video-${box.id}`}
              className="input--file"
              type="file"
              accept="video/*"
              onChange={(e) => setVideoFile(e.currentTarget.files?.[0] ?? null)}
            />
            <label htmlFor={`video-${box.id}`} className="input--file-label">
              {videoFile ? (
                <span className="input--file-label__filename">{videoFile.name}</span>
              ) : (
                'Choose video file…'
              )}
            </label>
          </span>
          <div className="field__help">
            Tip: slowly pan inside the open box. After upload, items become searchable.
          </div>
        </div>
        {uploadError ? <div className="alert alert--error">{uploadError}</div> : null}
        <button className="button button--primary" type="submit" disabled={!videoFile || uploading}>
          {uploading ? 'Uploading…' : box.has_video ? 'Upload new scan' : 'Upload scan'}
        </button>
      </form>

      <div className="divider" />

      <div className="form">
        {deleteError ? <div className="alert alert--error">{deleteError}</div> : null}
        <button
          type="button"
          className="button button--danger"
          disabled={deleting}
          onClick={async () => {
            if (!window.confirm(`Remove box “${box.label}”? This cannot be undone.`)) return
            setDeleteError(null)
            setDeleting(true)
            try {
              await deleteBox(box.id)
              await onRefresh()
              onDeleted()
            } catch (err) {
              setDeleteError(err instanceof Error ? err.message : 'Failed to remove box')
            } finally {
              setDeleting(false)
            }
          }}
        >
          {deleting ? 'Removing…' : 'Remove box'}
        </button>
      </div>
    </section>
  )
}

function SearchScreen(props: { boxes: BoxResponse[]; onSelectBox: (id: number) => void }) {
  const { onSelectBox } = props

  const [q, setQ] = useState('')
  const [results, setResults] = useState<SearchHit[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSearch(e: React.FormEvent) {
    e.preventDefault()
    const query = q.trim()
    if (!query) return
    setLoading(true)
    setError(null)
    try {
      const res = await searchBoxes(query)
      setResults(res.results)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="stack">
      <section className="card">
        <div className="card__title">Where is…?</div>
        <div className="card__subtitle">Search in plain language. We return the box and location.</div>
        <form className="form" onSubmit={onSearch}>
          <label className="field">
            <div className="field__label">Search</div>
            <input
              className="input"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder='e.g. "allen key", "passport", "Makita battery"'
            />
          </label>
          {error ? <div className="alert alert--error">{error}</div> : null}
          <button className="button button--primary" type="submit" disabled={loading}>
            {loading ? 'Searching…' : 'Search'}
          </button>
        </form>
      </section>

      <section className="card">
        <div className="card__title">Results</div>
        {results == null ? (
          <div className="muted">Run a search to see matches.</div>
        ) : results.length === 0 ? (
          <div className="muted">No matches yet. Try scanning more boxes.</div>
        ) : (
          <div className="list">
            {results.map((hit) => (
              <button
                key={`${hit.box_id}-${hit.score}`}
                type="button"
                className="listItem"
                onClick={() => onSelectBox(hit.box_id)}
              >
                <div className="listItem__title">{hit.box_label}</div>
                <div className="listItem__subtitle">
                  <span className="listItem__score">
                    {typeof hit.score === 'number' && hit.score <= 1
                      ? `${Math.round(hit.score * 100)}% match`
                      : `Score ${hit.score}`}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

export default App
