export function ModelHealthPanel({ models }) {
  if (!models || models.length === 0) {
    return (
      <div className="model-health">
        <h3>模型健康状态</h3>
        <p style={{ color: '#94a3b8' }}>暂无模型数据</p>
      </div>
    )
  }

  const statusMap = {
    healthy: { label: '健康', class: 'healthy' },
    degraded: { label: '降级', class: 'degraded' },
    unavailable: { label: '不可用', class: 'unavailable' }
  }

  return (
    <div className="model-health">
      <h3>模型健康状态</h3>
      {models.map((model, idx) => {
        const status = model.is_available ? 'healthy' : (model.degraded_reason ? 'degraded' : 'unavailable')
        const statusInfo = statusMap[status]
        return (
          <div className="model-item" key={idx}>
            <span className="model-name">{model.model}</span>
            <div className="model-status">
              <span className={`badge ${statusInfo.class}`}>
                {statusInfo.label}
              </span>
              {model.degraded_reason && (
                <span style={{ color: '#94a3b8', fontSize: 12 }}>{model.degraded_reason}</span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
