import { useEffect, useMemo, useState } from 'react'
import {
  ApiError,
  createBox,
  listBoxes,
  searchBoxes,
  updateBox,
  uploadBoxVideo,
  type BoxResponse,
  type SearchHit,
} from './api'

type Tab = 'boxes' | 'search'

function formatBoxSubtitle(box: BoxResponse) {
  const parts: string[] = []
  if (box.location) parts.push(box.location)
  parts.push(box.has_video ? 'scanned' : 'not scanned')
  return parts.join(' • ')
}

function App() {
  const [tab, setTab] = useState<Tab>('boxes')
  const [boxes, setBoxes] = useState<BoxResponse[] | null>(null)
  const [boxesError, setBoxesError] = useState<string | null>(null)
  const [boxesLoading, setBoxesLoading] = useState(false)

  const [selectedBoxId, setSelectedBoxId] = useState<number | null>(null)

  const selectedBox = useMemo(
    () => boxes?.find((b) => b.id === selectedBoxId) ?? null,
    [boxes, selectedBoxId],
  )

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
        <div className="topbar__title">BoxBrain</div>
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
  onSelectBox: (id: number) => void
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
        <BoxDetailCard key={selectedBox.id} box={selectedBox} onRefresh={onRefresh} />
      ) : null}
    </div>
  )
}

function BoxDetailCard(props: { box: BoxResponse; onRefresh: () => Promise<void> }) {
  const { box, onRefresh } = props
  const [location, setLocation] = useState(box.location ?? '')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

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
      setUploadError(err instanceof Error ? err.message : 'Upload failed')
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
          <input
            className="input"
            type="file"
            accept="video/*"
            onChange={(e) => setVideoFile(e.currentTarget.files?.[0] ?? null)}
          />
          <div className="field__help">
            Tip: slowly pan inside the open box. After upload, items become searchable.
          </div>
        </div>
        {uploadError ? <div className="alert alert--error">{uploadError}</div> : null}
        <button className="button button--primary" type="submit" disabled={!videoFile || uploading}>
          {uploading ? 'Uploading…' : box.has_video ? 'Upload new scan' : 'Upload scan'}
        </button>
      </form>
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
                <div className="listItem__subtitle">Score {hit.score}</div>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

export default App
