import { useState, useEffect } from 'react'
import { useWebSocket } from './useWebSocket'
import { fetchOverview, fetchTimeseries, fetchTopErrors, fetchRecentErrors } from './api'
import { ChatInterface } from './components/ChatInterface'
import { MetricCard } from './components/MetricCard'
import { TimeseriesChart } from './components/TimeseriesChart'
import { ErrorAnalysis } from './components/ErrorAnalysis'
import { ModelHealthPanel } from './components/ModelHealthPanel'

function App() {
  const [overview, setOverview] = useState(null)
  const [timeseries, setTimeseries] = useState([])
  const [topErrors, setTopErrors] = useState([])
  const [recentErrors, setRecentErrors] = useState([])
  const [timeRange, setTimeRange] = useState(5)
  const [chartRange, setChartRange] = useState(15)
  const [selectedModel, setSelectedModel] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')

  const { connected, connecting, onData } = useWebSocket()

  useEffect(() => {
    const loadInitialData = async () => {
      const [overviewData, tsData, topErr, recentErr] = await Promise.all([
        fetchOverview(timeRange),
        fetchTimeseries(chartRange, selectedModel),
        fetchTopErrors(),
        fetchRecentErrors(),
      ])
      setOverview(overviewData)
      setTimeseries(tsData.data || [])
      setTopErrors(topErr.errors || [])
      setRecentErrors(recentErr.errors || [])
    }
    loadInitialData()
  }, [timeRange, chartRange, selectedModel])

  useEffect(() => {
    const unsub = onData((data) => {
      if (data.type === 'timeseries_update') {
        setOverview(prev => prev ? { ...prev, model_health: data.model_health } : prev)
        fetchTimeseries(chartRange, selectedModel).then(ts => {
          setTimeseries(ts.data || [])
        })
      }
    })
    return unsub
  }, [onData, chartRange, selectedModel])

  const models = overview?.model_health?.map(m => m.model) || []

  return (
    <div className="app split-layout">
      {/* 左侧 - 对话界面 */}
      <div className="left-panel">
        <ChatInterface />
      </div>

      {/* 右侧 - 可视化平台 */}
      <div className="right-panel">
        <div className="header">
          <h1>模型可视化平台</h1>
          <div className="connection-status">
            <span className={`status-dot ${connected ? '' : connecting ? 'connecting' : 'disconnected'}`} />
            <span>{connected ? '已连接' : connecting ? '连接中...' : '已断开'}</span>
          </div>
        </div>

        <div className="viz-tabs">
          <button 
            className={activeTab === 'overview' ? 'active' : ''} 
            onClick={() => setActiveTab('overview')}
          >
            概览
          </button>
          <button 
            className={activeTab === 'errors' ? 'active' : ''} 
            onClick={() => setActiveTab('errors')}
          >
            错误分析
          </button>
        </div>

        {activeTab === 'overview' && (
          <>
            <div className="chart-controls" style={{ marginBottom: 20 }}>
              <span style={{ color: '#94a3b8', marginRight: 8 }}>视图:</span>
              {[5, 15, 60].map(m => (
                <button key={m} className={timeRange === m ? 'active' : ''} onClick={() => setTimeRange(m)}>
                  {m}分钟
                </button>
              ))}
              <select
                value={selectedModel || ''}
                onChange={(e) => setSelectedModel(e.target.value || null)}
                style={{ marginLeft: 'auto', padding: '6px 12px', background: '#1e293b', color: '#cbd5e1', border: '1px solid #475569', borderRadius: 6 }}
              >
                <option value="">所有模型</option>
                {models.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>

            <div className="metrics-grid">
              <MetricCard label="QPS" value={overview?.qps?.toFixed(2) || '0.00'} />
              <MetricCard label="成功率" value={`${((overview?.success_rate || 0) * 100).toFixed(1)}%`} type="success" />
              <MetricCard label="P50 延迟" value={`${(overview?.p50_latency || 0).toFixed(0)}ms`} />
              <MetricCard label="P95 延迟" value={`${(overview?.p95_latency || 0).toFixed(0)}ms`} />
              <MetricCard label="错误率" value={`${((overview?.error_rate || 0) * 100).toFixed(1)}%`} type={(overview?.error_rate || 0) > 0.05 ? 'error' : 'success'} />
            </div>

            <div className="charts-section">
              <TimeseriesChart data={timeseries} title="QPS 趋势" dataKey="qps" color="#3b82f6" timeRange={chartRange} setTimeRange={setChartRange} />
              <TimeseriesChart data={timeseries} title="延迟趋势 (P95)" dataKey="p95_latency" color="#f59e0b" timeRange={chartRange} setTimeRange={setChartRange} unit="ms" />
            </div>

            <div className="charts-section">
              <ModelHealthPanel models={overview?.model_health || []} />
            </div>
          </>
        )}

        {activeTab === 'errors' && (
          <ErrorAnalysis topErrors={topErrors} recentErrors={recentErrors} />
        )}
      </div>
    </div>
  )
}

export default App
