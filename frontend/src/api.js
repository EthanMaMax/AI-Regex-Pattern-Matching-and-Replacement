import axios from "axios"

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api",
})

export function getApiErrorMessage(err, fallback) {
  const detail = err.response?.data?.detail
  if (typeof detail === "string") {
    return detail
  }
  return fallback
}

export async function uploadDataset(file) {
  const formData = new FormData()
  formData.append("file", file)

  const response = await api.post("/upload/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  })

  return response.data
}

export async function replaceInDataset({ datasetId, column, regex, replacement }) {
  const response = await api.post("/replace/", {
    dataset_id: datasetId,
    column,
    regex,
    replacement,
  })

  return response.data
}

export async function naturalLanguageReplace({ datasetId, naturalLanguage }) {
  const response = await api.post("/natural-language-replace/", {
    dataset_id: datasetId,
    natural_language: naturalLanguage,
  })

  return response.data
}

export function getDownloadUrl(datasetId) {
  return `${api.defaults.baseURL}/download/${datasetId}/`
}

export async function deleteDataset(datasetId) {
  if (!datasetId) {
    return
  }
  await api.delete(`/datasets/${datasetId}/`)
}

export function beaconDeleteDataset(datasetId) {
  if (!datasetId || !navigator.sendBeacon) {
    return false
  }

  return navigator.sendBeacon(`${api.defaults.baseURL}/datasets/${datasetId}/`)
}

export async function undoDataset(datasetId) {
  const response = await api.post(`/datasets/${datasetId}/undo/`)
  return response.data
}

export async function redoDataset(datasetId) {
  const response = await api.post(`/datasets/${datasetId}/redo/`)
  return response.data
}
