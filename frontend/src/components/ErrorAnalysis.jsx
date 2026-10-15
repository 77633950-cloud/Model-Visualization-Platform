export function ErrorAnalysis({ topErrors, recentErrors }) {
  return (
    <div className="errors-section">
      <h3>错误分析</h3>
      
      <h4 style={{ color: '#94a3b8', marginBottom: 12, marginTop: 16 }}>错误类型排行</h4>
      {topErrors && topErrors.length > 0 ? (
        <table className="error-table">
          <thead>
            <tr>
              <th>错误类型</th>
              <th>次数</th>
              <th>最近出现</th>
            </tr>
          </thead>
          <tbody>
            {topErrors.map((err, idx) => (
              <tr key={idx}>
                <td className="error-type">{err.error_type}</td>
                <td>{err.count}</td>
                <td>{new Date(err.last_seen).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p style={{ color: '#94a3b8', padding: '20px 0' }}>暂无错误记录</p>
      )}

      <h4 style={{ color: '#94a3b8', marginBottom: 12, marginTop: 24 }}>最近错误请求</h4>
      {recentErrors && recentErrors.length > 0 ? (
        <table className="error-table">
          <thead>
            <tr>
              <th>请求ID</th>
              <th>模型</th>
              <th>错误类型</th>
              <th>延迟</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            {recentErrors.slice(0, 10).map((err, idx) => (
              <tr key={idx}>
                <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{err.request_id.slice(0, 8)}...</td>
                <td>{err.model}</td>
                <td className="error-type">{err.error_type}</td>
                <td>{err.latency_ms.toFixed(0)}ms</td>
                <td>{new Date(err.timestamp).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p style={{ color: '#94a3b8', padding: '20px 0' }}>暂无最近错误</p>
      )}
    </div>
  )
}
