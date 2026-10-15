export function MetricCard({ label, value, type = 'default' }) {
  return (
    <div className="metric-card">
      <h3>{label}</h3>
      <div className={`metric-value ${type}`}>{value}</div>
    </div>
  )
}
