import { useEffect, useMemo, useRef, useState } from "react"
import {
  beaconDeleteDataset,
  deleteDataset,
  getApiErrorMessage,
  getDownloadUrl,
  naturalLanguageReplace,
  redoDataset,
  undoDataset,
  uploadDataset,
} from "./api"

function App() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [dataset, setDataset] = useState(null)
  const [error, setError] = useState("")
  const [isUploading, setIsUploading] = useState(false)
  const [replaceMessage, setReplaceMessage] = useState("")
  const [replaceError, setReplaceError] = useState("")
  const [naturalLanguage, setNaturalLanguage] = useState("")
  const [isNaturalReplacing, setIsNaturalReplacing] = useState(false)
  const [generatedPlan, setGeneratedPlan] = useState(null)
  const [isHistoryLoading, setIsHistoryLoading] = useState(false)
  const activeDatasetIdRef = useRef(null)

  const previewRows = dataset?.preview ?? []
  const columns = useMemo(() => dataset?.columns ?? [], [dataset])

  useEffect(() => {
    activeDatasetIdRef.current = dataset?.dataset_id ?? null
  }, [dataset?.dataset_id])

  useEffect(() => {
    function handlePageHide() {
      beaconDeleteDataset(activeDatasetIdRef.current)
    }

    window.addEventListener("pagehide", handlePageHide)
    return () => {
      window.removeEventListener("pagehide", handlePageHide)
    }
  }, [])

  async function handleSubmit(event) {
    event.preventDefault()
    if (!selectedFile) {
      setError("Choose a CSV or Excel file first.")
      return
    }

    setIsUploading(true)
    setError("")
    if (dataset?.dataset_id) {
      await deleteDataset(dataset.dataset_id).catch(() => {})
    }
    setDataset(null)
    setReplaceError("")
    setReplaceMessage("")
    setGeneratedPlan(null)

    try {
      const result = await uploadDataset(selectedFile)
      setDataset(result)
    } catch (err) {
      setError(getApiErrorMessage(err, "Upload failed. Check the backend server and file format."))
    } finally {
      setIsUploading(false)
    }
  }

  async function handleNaturalLanguageReplace(event) {
    event.preventDefault()
    if (!dataset?.dataset_id) {
      setReplaceError("Upload a dataset first.")
      return
    }
    if (!naturalLanguage.trim()) {
      setReplaceError("Enter a natural language replacement request.")
      return
    }

    setIsNaturalReplacing(true)
    setReplaceError("")
    setReplaceMessage("")
    setGeneratedPlan(null)

    try {
      const result = await naturalLanguageReplace({
        datasetId: dataset.dataset_id,
        naturalLanguage,
      })
      setDataset((currentDataset) => ({
        ...currentDataset,
        ...result,
      }))
      setGeneratedPlan({
        columns: result.generated_columns ?? [result.generated_column].filter(Boolean),
        regex: result.generated_regex,
        replacement: result.replacement,
      })
      setNaturalLanguage("")
      setReplaceMessage(`LLM replacement applied. ${result.changed_cells ?? result.match_count} cell(s) changed.`)
    } catch (err) {
      setReplaceError(getApiErrorMessage(err, "Natural language replacement failed."))
    } finally {
      setIsNaturalReplacing(false)
    }
  }

  async function handleUndo() {
    if (!dataset?.dataset_id) {
      return
    }
    setIsHistoryLoading(true)
    setReplaceError("")
    setReplaceMessage("")

    try {
      const result = await undoDataset(dataset.dataset_id)
      setDataset((currentDataset) => ({
        ...currentDataset,
        ...result,
      }))
      setReplaceMessage("Undo applied.")
    } catch (err) {
      setReplaceError(getApiErrorMessage(err, "Undo failed."))
    } finally {
      setIsHistoryLoading(false)
    }
  }

  async function handleRedo() {
    if (!dataset?.dataset_id) {
      return
    }
    setIsHistoryLoading(true)
    setReplaceError("")
    setReplaceMessage("")

    try {
      const result = await redoDataset(dataset.dataset_id)
      setDataset((currentDataset) => ({
        ...currentDataset,
        ...result,
      }))
      setReplaceMessage("Redo applied.")
    } catch (err) {
      setReplaceError(getApiErrorMessage(err, "Redo failed."))
    } finally {
      setIsHistoryLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-zinc-100 text-zinc-950">
      <div className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-5 py-6 md:flex-row md:items-end md:justify-between">
          <section className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span className="rounded-md bg-teal-50 px-2 py-1 text-xs font-semibold uppercase tracking-wide text-teal-800">
                AI CSV
              </span>
              <span className="text-xs font-medium text-zinc-500">Regex data processor</span>
            </div>
            <h1 className="text-2xl font-semibold tracking-normal md:text-3xl">
              Pattern matching and replacement
            </h1>
            <p className="max-w-2xl text-sm leading-6 text-zinc-600">
              Upload a CSV or Excel file, describe the transformation in plain English, preview the updated data, and download the processed CSV.
            </p>
          </section>

          <div className="flex flex-wrap gap-2 text-xs font-medium text-zinc-600">
            <StatusPill label="CSV" />
            <StatusPill label="XLSX" />
            <StatusPill label="OpenAI regex" />
          </div>
        </div>
      </div>

      <div className="mx-auto grid w-full max-w-7xl gap-5 px-5 py-6 lg:grid-cols-[420px_minmax(0,1fr)]">
        <aside className="flex flex-col gap-5">
          <section className="rounded-lg border border-zinc-200 bg-white shadow-sm">
            <div className="border-b border-zinc-200 px-5 py-4">
              <h2 className="text-sm font-semibold text-zinc-950">Source file</h2>
              <p className="mt-1 text-sm text-zinc-600">Upload one spreadsheet to start a temporary processing session.</p>
            </div>
            <form className="grid gap-4 p-5" onSubmit={handleSubmit}>
              <label className="flex flex-col gap-2 text-sm font-medium text-zinc-700">
                Data file
                <input
                  className="block w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 file:mr-4 file:rounded-md file:border-0 file:bg-teal-700 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-teal-800"
                  type="file"
                  accept=".csv,.xls,.xlsx"
                  onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                />
              </label>
              <button
                className="h-10 rounded-md bg-zinc-950 px-5 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
                type="submit"
                disabled={isUploading}
              >
                {isUploading ? "Uploading..." : "Upload and preview"}
              </button>
            </form>

            {error ? (
              <div className="mx-5 mb-5 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </div>
            ) : null}
          </section>

          {dataset ? (
            <>
              <section className="rounded-lg border border-zinc-200 bg-white shadow-sm">
                <div className="border-b border-zinc-200 px-5 py-4">
                  <h2 className="text-sm font-semibold text-zinc-950">Natural language transformation</h2>
                  <p className="mt-1 text-xs text-zinc-500">Examples: redact emails, replace names, or apply replacements to specific columns.</p>
                </div>
                <form className="flex flex-col gap-4" onSubmit={handleNaturalLanguageReplace}>
                  <label className="flex flex-col gap-2 text-sm font-medium text-zinc-700">
                    <span className="px-5 pt-5">Request</span>
                    <textarea
                      className="mx-5 min-h-36 resize-y rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm leading-6 text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-teal-700 focus:ring-2 focus:ring-teal-100"
                      placeholder="Find email addresses in the EMAIL column and replace them with 'REDACTED'."
                      value={naturalLanguage}
                      onChange={(event) => setNaturalLanguage(event.target.value)}
                    />
                  </label>
                  <button
                    className="mx-5 mb-5 h-10 rounded-md bg-zinc-950 px-5 text-sm font-semibold text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
                    type="submit"
                    disabled={isNaturalReplacing}
                  >
                  {isNaturalReplacing ? "Generating..." : "Generate regex and apply"}
                </button>
              </form>

              {replaceError ? (
                <div className="mx-5 mb-5 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {replaceError}
                </div>
              ) : null}

              {/*
              {generatedPlan ? (
                <div className="mx-5 mb-5 grid gap-3 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-sm">
                  <GeneratedPlanItem label="Columns" value={generatedPlan.columns.join(", ")} />
                  <GeneratedPlanItem label="Regex" value={generatedPlan.regex} mono />
                  <GeneratedPlanItem label="Replacement" value={generatedPlan.replacement || "(empty)"} />
                </div>
              ) : null}
              */}
              </section>
            </>
          ) : null}
        </aside>

        <section className="min-w-0">
          {dataset ? (
            <div className="grid gap-5">
              <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <Metric label="File" value={dataset.filename} />
                <Metric label="Rows" value={dataset.row_count} />
                <Metric label="Columns" value={dataset.column_count} />
                <Metric label="Preview" value={`${previewRows.length} rows`} />
              </section>

              <div className="overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-sm">
                <div className="flex flex-wrap items-center gap-2 border-b border-zinc-200 px-5 py-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-base font-semibold">Data Preview</h2>
                    <button
                      className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm font-semibold text-zinc-800 transition hover:bg-zinc-100 disabled:cursor-not-allowed disabled:border-zinc-200 disabled:text-zinc-400"
                      type="button"
                      disabled={!dataset.can_undo || isHistoryLoading}
                      onClick={handleUndo}
                    >
                      Undo
                    </button>
                    <button
                      className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm font-semibold text-zinc-800 transition hover:bg-zinc-100 disabled:cursor-not-allowed disabled:border-zinc-200 disabled:text-zinc-400"
                      type="button"
                      disabled={!dataset.can_redo || isHistoryLoading}
                      onClick={handleRedo}
                    >
                      Redo
                    </button>
                  </div>
                  {replaceMessage ? (
                    <div className="rounded-md border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-800">
                      {replaceMessage}
                    </div>
                  ) : null}
                  <a
                    className="ml-auto w-fit rounded-md bg-zinc-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-zinc-800"
                    href={getDownloadUrl(dataset.dataset_id)}
                  >
                    Download
                  </a>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-zinc-200 text-left text-sm">
                    <thead className="bg-zinc-50">
                      <tr>
                        {columns.map((column) => (
                          <th className="whitespace-nowrap px-5 py-3 text-xs font-semibold uppercase text-zinc-600" key={column}>
                            {column}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100">
                      {previewRows.map((row, rowIndex) => (
                        <tr className="hover:bg-zinc-50" key={rowIndex}>
                          {columns.map((column) => (
                            <td className="max-w-sm truncate px-5 py-3 text-zinc-700" key={column}>
                              {formatCell(row[column])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex min-h-[520px] items-center justify-center rounded-lg border border-dashed border-zinc-300 bg-white px-5 py-10 text-center">
              <div>
            <h2 className="text-sm font-semibold text-zinc-900">No dataset loaded</h2>
            <p className="mt-2 text-sm text-zinc-500">Upload a CSV or Excel file to preview and transform your data.</p>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  )
}

function StatusPill({ label }) {
  return (
    <span className="rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1">
      {label}
    </span>
  )
}

function Metric({ label, value }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white px-4 py-3 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-zinc-900">{value}</p>
    </div>
  )
}

function GeneratedPlanItem({ label, value, mono = false }) {
  return (
    <div className="min-w-0">
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</p>
      <p className={`mt-1 overflow-x-auto whitespace-nowrap text-sm font-semibold text-zinc-900 ${mono ? "font-mono" : ""}`}>
        {value}
      </p>
    </div>
  )
}

function formatCell(value) {
  if (value === null || value === undefined || value === "") {
    return "-"
  }
  return String(value)
}

export default App
