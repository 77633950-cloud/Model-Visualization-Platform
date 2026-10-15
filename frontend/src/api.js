export async function fetchOverview(minutes = 5) {
  const res = await fetch(`/api/metrics/overview?minutes=${minutes}`)
  return res.json()
}

export async function fetchTimeseries(minutes = 60, model = null) {
  const url = model
    ? `/api/metrics/timeseries?minutes=${minutes}&model=${model}`
    : `/api/metrics/timeseries?minutes=${minutes}`
  const res = await fetch(url)
  return res.json()
}

export async function fetchTopErrors(limit = 10) {
  const res = await fetch(`/api/errors/top?limit=${limit}`)
  return res.json()
}

export async function fetchRecentErrors(limit = 20) {
  const res = await fetch(`/api/errors/recent?limit=${limit}`)
  return res.json()
}
