import { useCallback, useEffect, useMemo, useState } from 'react'
import QRCode from 'react-qr-code'
import {
  ApiError,
  createBox,
  createLocation,
  deleteBox,
  deleteLocation,
  getBoxImageUrl,
  getLanIpv4,
  listBoxes,
  listLocations,
  searchBoxes,
  updateBox,
  uploadBoxVideo,
  webappUrlForLanHost,
  type BoxResponse,
  type LocationResponse,
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

const DEFAULT_LOCATION_COLOR = '#5dd9f7'

type Tab = 'boxes' | 'search' | 'locations'

type PhoneQrState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ok'; url: string }
  | { status: 'error'; message: string }

function BoxListSubtitle({ box }: { box: BoxResponse }) {
  return (
    <>
      {box.location ? (
        <>
          {box.location_color ? (
            <span
              className="location-dot"
              style={{ backgroundColor: box.location_color }}
              aria-hidden
            />
          ) : null}
          <span>{box.location}</span>
          {' • '}
        </>
      ) : null}
      {box.has_video ? 'scanned' : 'not scanned'}
    </>
  )
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
  const [locations, setLocations] = useState<LocationResponse[] | null>(null)
  const [locationsError, setLocationsError] = useState<string | null>(null)

  const refreshLocations = useCallback(async () => {
    setLocationsError(null)
    try {
      setLocations(await listLocations())
    } catch (e) {
      setLocationsError(e instanceof Error ? e.message : 'Failed to load locations')
    }
  }, [])

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

  useEffect(() => {
    if (tab === 'boxes' || tab === 'locations') void refreshLocations()
  }, [tab, refreshLocations])

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
          <button
            type="button"
            className={tab === 'locations' ? 'tab tab--active' : 'tab'}
            onClick={() => setTab('locations')}
            role="tab"
            aria-selected={tab === 'locations'}
          >
            Locations
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
            locations={locations}
            locationsError={locationsError}
            onRefreshLocations={refreshLocations}
          />
        ) : tab === 'locations' ? (
          <LocationsScreen
            locations={locations}
            locationsError={locationsError}
            onRefresh={refreshLocations}
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
  locations: LocationResponse[] | null
  locationsError: string | null
  onRefreshLocations: () => Promise<void>
}) {
  const {
    boxes,
    boxesError,
    boxesLoading,
    selectedBoxId,
    onSelectBox,
    onRefresh,
    selectedBox,
    locations,
    locationsError,
    onRefreshLocations,
  } = props

  const [createLabel, setCreateLabel] = useState('')
  const [createLocationId, setCreateLocationId] = useState<number | null>(null)
  const [createError, setCreateError] = useState<string | null>(null)
  const [createLoading, setCreateLoading] = useState(false)

  const createLocColor =
    createLocationId != null ? locations?.find((l) => l.id === createLocationId)?.color : undefined

  const [drilldownLocationId, setDrilldownLocationId] = useState<number | null | undefined>(undefined)

  const unassignedColor = '#94a3b8'
  const unassignedBoxesCount = boxes?.filter((b) => b.location_id == null).length ?? 0
  const locationsWithBoxes =
    boxes && locations
      ? locations
          .map((loc) => ({
            id: loc.id,
            name: loc.name,
            color: loc.color,
            count: boxes.filter((b) => b.location_id === loc.id).length,
          }))
          .filter((x) => x.count > 0)
      : []

  const locationItems =
    drilldownLocationId === undefined
      ? [
          ...locationsWithBoxes,
          ...(unassignedBoxesCount > 0
            ? [{ id: null as number | null, name: 'Unassigned', color: unassignedColor, count: unassignedBoxesCount }]
            : []),
        ]
      : []

  async function onCreate(e: React.FormEvent) {
    e.preventDefault()
    setCreateError(null)
    setCreateLoading(true)
    try {
      const box = await createBox({
        label: createLabel.trim(),
        location_id: createLocationId,
      })
      setCreateLabel('')
      setCreateLocationId(null)
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
          Label the physical box, then scan a 5–10s video of the open box. Pick a saved location or add
          one under the Locations tab.
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
            <div className="field-row">
              <select
                className="input input--select"
                value={createLocationId ?? ''}
                onChange={(e) => {
                  const v = e.target.value
                  setCreateLocationId(v === '' ? null : Number(v))
                }}
                disabled={locations == null}
              >
                <option value="">None</option>
                {(locations ?? []).map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.name}
                  </option>
                ))}
              </select>
              {createLocColor ? (
                <span
                  className="location-dot location-dot--lg"
                  style={{ backgroundColor: createLocColor }}
                  title={createLocColor}
                  aria-hidden
                />
              ) : null}
            </div>
            {locationsError ? <div className="field__help field__help--error">{locationsError}</div> : null}
            {locations && locations.length === 0 ? (
              <div className="field__help">No saved locations yet — create some in the Locations tab.</div>
            ) : null}
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
              Tap a location to view its boxes. Tap a box to edit it (scan, location, label).
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
          <>
            {drilldownLocationId !== undefined ? (
              <div className="row row--space" style={{ marginTop: 12 }}>
                <button
                  className="button button--ghost"
                  type="button"
                  onClick={() => setDrilldownLocationId(undefined)}
                >
                  Back
                </button>
                <div className="muted">
                  {drilldownLocationId === null ? 'Unassigned' : locations?.find((l) => l.id === drilldownLocationId)?.name ?? 'Location'}{' '}
                  • {boxes.filter((b) => b.location_id === drilldownLocationId).length} box
                  {boxes.filter((b) => b.location_id === drilldownLocationId).length === 1 ? '' : 'es'}
                </div>
              </div>
            ) : null}

            {drilldownLocationId === undefined ? (
              <div className="list">
                {locationItems.length === 0 ? (
                  <div className="muted">No locations yet. Assign a location to a box, or add one in the Locations tab.</div>
                ) : null}

                {locationItems.map((loc) => (
                  <button
                    key={loc.id ?? 'unassigned'}
                    type="button"
                    className="listItem"
                    onClick={() => setDrilldownLocationId(loc.id)}
                  >
                    <div className="listItem__title" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span
                        className="location-dot location-dot--lg"
                        style={{ backgroundColor: loc.color }}
                        aria-hidden
                      />
                      {loc.name}
                    </div>
                    <div className="listItem__subtitle">{loc.count} box{loc.count === 1 ? '' : 'es'}</div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="list">
                {boxes.filter((b) => b.location_id === drilldownLocationId).length === 0 ? (
                  <div className="muted">No boxes in this location.</div>
                ) : null}
                {boxes
                  .filter((b) => b.location_id === drilldownLocationId)
                  .map((box) => (
                    <button
                      key={box.id}
                      type="button"
                      className={box.id === selectedBoxId ? 'listItem listItem--active' : 'listItem'}
                      onClick={() => onSelectBox(box.id)}
                    >
                      <div className="listItem__title">{box.label}</div>
                      <div className="listItem__subtitle">
                        <BoxListSubtitle box={box} />
                      </div>
                    </button>
                  ))}
              </div>
            )}
          </>
        ) : null}
      </section>

      {selectedBox ? (
        <BoxDetailCard
          key={selectedBox.id}
          box={selectedBox}
          locations={locations}
          locationsError={locationsError}
          onRefresh={onRefresh}
          onRefreshLocations={onRefreshLocations}
          onDeleted={() => onSelectBox(null)}
        />
      ) : null}
    </div>
  )
}

function BoxDetailCard(props: {
  box: BoxResponse
  locations: LocationResponse[] | null
  locationsError: string | null
  onRefresh: () => Promise<void>
  onRefreshLocations: () => Promise<void>
  onDeleted: () => void
}) {
  const { box, locations, locationsError, onRefresh, onRefreshLocations, onDeleted } = props
  const [labelDraft, setLabelDraft] = useState(box.label)
  const [labelSaving, setLabelSaving] = useState(false)
  const [labelError, setLabelError] = useState<string | null>(null)

  useEffect(() => {
    setLabelDraft(box.label)
  }, [box.id, box.label])

  const [locationId, setLocationId] = useState<number | null>(box.location_id ?? null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    setLocationId(box.location_id ?? null)
  }, [box.id, box.location_id])

  const detailLocColor =
    locationId != null ? locations?.find((l) => l.id === locationId)?.color : undefined

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
      await updateBox(box.id, { location_id: locationId })
      await onRefresh()
      void onRefreshLocations()
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to update')
    } finally {
      setSaving(false)
    }
  }

  async function onSaveLabel(e: React.FormEvent) {
    e.preventDefault()
    setLabelError(null)
    setLabelSaving(true)
    try {
      await updateBox(box.id, { label: labelDraft.trim() })
      await onRefresh()
    } catch (err) {
      setLabelError(err instanceof Error ? err.message : 'Failed to update label')
    } finally {
      setLabelSaving(false)
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

      <form className="form" onSubmit={onSaveLabel}>
        <label className="field">
          <div className="field__label">Box label</div>
          <input
            className="input"
            value={labelDraft}
            onChange={(e) => setLabelDraft(e.target.value)}
            placeholder="e.g. attic_underscore_1"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            required
          />
        </label>
        {labelError ? <div className="alert alert--error">{labelError}</div> : null}
        <button className="button button--primary" type="submit" disabled={labelSaving}>
          {labelSaving ? 'Saving…' : 'Save label'}
        </button>
      </form>

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
          <div className="field-row">
            <select
              className="input input--select"
              value={locationId ?? ''}
              onChange={(e) => {
                const v = e.target.value
                setLocationId(v === '' ? null : Number(v))
              }}
              disabled={locations == null}
            >
              <option value="">None</option>
              {(locations ?? []).map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.name}
                </option>
              ))}
            </select>
            {detailLocColor ? (
              <span
                className="location-dot location-dot--lg"
                style={{ backgroundColor: detailLocColor }}
                title={detailLocColor}
                aria-hidden
              />
            ) : null}
          </div>
          {locationsError ? <div className="field__help field__help--error">{locationsError}</div> : null}
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

function LocationsScreen(props: {
  locations: LocationResponse[] | null
  locationsError: string | null
  onRefresh: () => Promise<void>
}) {
  const { locations, locationsError, onRefresh } = props
  const [locName, setLocName] = useState('')
  const [locColor, setLocColor] = useState(DEFAULT_LOCATION_COLOR)
  const [creating, setCreating] = useState(false)
  const [createErr, setCreateErr] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  async function onCreateLocation(e: React.FormEvent) {
    e.preventDefault()
    const name = locName.trim()
    if (!name) return
    setCreateErr(null)
    setCreating(true)
    try {
      await createLocation({ name, color: locColor })
      setLocName('')
      setLocColor(DEFAULT_LOCATION_COLOR)
      await onRefresh()
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setCreateErr('A location with that name already exists.')
      } else {
        setCreateErr(err instanceof Error ? err.message : 'Failed to create location')
      }
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="stack">
      <section className="card">
        <div className="card__title">New location</div>
        <div className="card__subtitle">
          Name a place (room, shelf, storage unit) and pick a color. Boxes can be assigned from a
          dropdown.
        </div>
        <form className="form" onSubmit={onCreateLocation}>
          <label className="field">
            <div className="field__label">Name</div>
            <input
              className="input"
              value={locName}
              onChange={(e) => setLocName(e.target.value)}
              placeholder="e.g. Garage — east wall"
              required
            />
          </label>
          <label className="field">
            <div className="field__label">Color</div>
            <div className="field-row field-row--color">
              <input
                type="color"
                className="input input--color"
                value={locColor}
                onChange={(e) => setLocColor(e.target.value)}
                aria-label="Location color"
              />
              <span className="mono input--color-hex">{locColor}</span>
            </div>
          </label>
          {createErr ? <div className="alert alert--error">{createErr}</div> : null}
          {locationsError ? <div className="alert alert--error">{locationsError}</div> : null}
          <button className="button button--primary" type="submit" disabled={creating}>
            {creating ? 'Saving…' : 'Save location'}
          </button>
        </form>
      </section>

      <section className="card">
        <div className="card__title">Saved locations</div>
        <div className="card__subtitle">Used in the box list and when creating or editing a box.</div>
        {locations == null ? (
          <div className="muted">Loading…</div>
        ) : locations.length === 0 ? (
          <div className="muted">No locations yet. Add one above.</div>
        ) : (
          <ul className="locations-list">
            {locations.map((loc) => (
              <li key={loc.id} className="locations-list__item">
                <span
                  className="location-dot location-dot--lg"
                  style={{ backgroundColor: loc.color }}
                  aria-hidden
                />
                <span className="locations-list__name">{loc.name}</span>
                <code className="locations-list__hex mono">{loc.color}</code>
                <button
                  type="button"
                  className="button button--ghost button--compact"
                  disabled={deletingId === loc.id}
                  onClick={async () => {
                    if (!window.confirm(`Remove location “${loc.name}”? Boxes using it will have no location.`))
                      return
                    setDeletingId(loc.id)
                    try {
                      await deleteLocation(loc.id)
                      await onRefresh()
                    } catch (err) {
                      window.alert(err instanceof Error ? err.message : 'Failed to remove')
                    } finally {
                      setDeletingId(null)
                    }
                  }}
                >
                  {deletingId === loc.id ? 'Removing…' : 'Remove'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
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
