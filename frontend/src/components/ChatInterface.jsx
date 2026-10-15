import { useState, useRef, useEffect } from 'react'

export function ChatInterface() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [model, setModel] = useState('glm-4-flash')
  const [apiKey, setApiKey] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const [apiKeyError, setApiKeyError] = useState('')
  const messagesEndRef = useRef(null)

  const models = [
    { value: 'glm-4-flash', label: '智谱 GLM-4-Flash (免费)', desc: '完全免费，适合日常使用' },
    { value: 'glm-4', label: '智谱 GLM-4', desc: '收费，性能更强' },
    { value: 'glm-4v', label: '智谱 GLM-4V (视觉)', desc: '支持图片理解' },
    { value: 'deepseek-chat', label: 'DeepSeek Chat', desc: '国产大模型' },
    { value: 'deepseek-coder', label: 'DeepSeek Coder', desc: '代码专用模型' },
  ]

  useEffect(() => {
    const savedApiKey = localStorage.getItem('zhipu_api_key')
    if (savedApiKey) {
      setApiKey(savedApiKey)
    }
  }, [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const saveApiKey = () => {
    if (apiKey.trim()) {
      localStorage.setItem('zhipu_api_key', apiKey.trim())
      setApiKeyError('')
    }
  }

  const clearApiKey = () => {
    localStorage.removeItem('zhipu_api_key')
    setApiKey('')
    setApiKeyError('')
  }

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const currentApiKey = apiKey.trim() || localStorage.getItem('zhipu_api_key')
    if (!currentApiKey) {
      setApiKeyError('请先配置 API Key')
      setShowSettings(true)
      return
    }

    const userMessage = input.trim()
    setInput('')
    setIsLoading(true)
    setApiKeyError('')

    setMessages(prev => [...prev, { role: 'user', content: userMessage, timestamp: new Date() }])

    try {
      const response = await fetch('/proxy/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${currentApiKey}`,
        },
        body: JSON.stringify({
          model: model,
          messages: [{ role: 'user', content: userMessage }],
          max_tokens: 1000,
        }),
      })

      const data = await response.json()

      if (response.ok) {
        let assistantMessage = ''
        if (data.choices && data.choices[0]) {
          const choice = data.choices[0]
          assistantMessage = choice.message?.content || choice.delta?.content || choice.text || '收到响应但无法解析内容'
        } else {
          assistantMessage = '响应格式异常'
        }
        setMessages(prev => [...prev, { role: 'assistant', content: assistantMessage, timestamp: new Date() }])
      } else {
        // 统一错误解析
        let errorMsg = '请求失败'
        if (data.error) {
          if (typeof data.error === 'string') {
            errorMsg = data.error
          } else if (data.error.message) {
            errorMsg = data.error.message
          } else if (data.error.type) {
            errorMsg = data.error.type
          }
        }
        setMessages(prev => [...prev, { role: 'assistant', content: `错误: ${errorMsg}`, timestamp: new Date(), isError: true }])

        if (response.status === 401) {
          setApiKeyError('API Key 无效或已过期，请重新配置')
        }
      }
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: `网络错误: ${error.message}`, timestamp: new Date(), isError: true }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
  }

  const currentModel = models.find(m => m.value === model)
  const hasApiKey = apiKey.trim() || localStorage.getItem('zhipu_api_key')

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <h2>API 对话测试</h2>
        <div className="chat-controls">
          <select value={model} onChange={(e) => setModel(e.target.value)} className="model-select">
            {models.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
          </select>
          <button onClick={() => setShowSettings(!showSettings)} className={`settings-btn ${!hasApiKey ? 'warning' : ''}`}>
            {!hasApiKey ? '⚠️ 配置 Key' : '设置'}
          </button>
          <button onClick={clearChat} className="clear-btn">清空</button>
        </div>
      </div>

      <div className={`apikey-panel ${showSettings ? 'show' : ''}`}>
        <div className="apikey-header">
          <h4>🔑 配置 API Key</h4>
          <a href="https://open.bigmodel.cn/usercenter/apikeys" target="_blank" rel="noopener noreferrer" className="get-key-link">
            获取免费 API Key →
          </a>
        </div>
        <div className="apikey-input-group">
          <input
            type="password"
            value={apiKey}
            onChange={(e) => { setApiKey(e.target.value); setApiKeyError('') }}
            placeholder="请输入你的 API Key"
            className={apiKeyError ? 'error' : ''}
          />
          <button onClick={saveApiKey} className="save-btn">保存</button>
          {hasApiKey && <button onClick={clearApiKey} className="clear-key-btn">清除</button>}
        </div>
        {apiKeyError && <div className="apikey-error">{apiKeyError}</div>}
        <div className="apikey-hint">
          <p>💡 提示：</p>
          <ul>
            <li>API Key 仅保存在浏览器本地</li>
            <li>推荐模型：GLM-4-Flash（完全免费）</li>
            <li>新用户注册智谱 AI 可获得免费额度</li>
          </ul>
        </div>
      </div>

      <div className="model-info">
        当前模型: <strong>{currentModel?.label}</strong>
        <span className="model-desc">{currentModel?.desc}</span>
        {!hasApiKey && <span className="no-key-warning">⚠️ 未配置 API Key</span>}
      </div>

      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-state">
            <p>👋 开始对话</p>
            <p className="hint">使用智谱 AI GLM-4-Flash 完全免费模型</p>
            {!hasApiKey && <p className="hint warning">⚠️ 请先点击右上角"配置 Key"按钮设置 API Key</p>}
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role} ${msg.isError ? 'error' : ''}`}>
              <div className="message-header">
                <span className="role">{msg.role === 'user' ? '你' : 'AI'}</span>
                <span className="time">{msg.timestamp.toLocaleTimeString()}</span>
              </div>
              <div className="message-content">{msg.content}</div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="message assistant loading">
            <div className="message-header"><span className="role">AI</span></div>
            <div className="message-content"><span className="typing">思考中...</span></div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-container">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={hasApiKey ? "输入消息，按 Enter 发送..." : "请先配置 API Key"}
          disabled={isLoading || !hasApiKey}
          rows={3}
        />
        <button onClick={sendMessage} disabled={isLoading || !input.trim() || !hasApiKey} className="send-btn">
          {isLoading ? '发送中...' : '发送'}
        </button>
      </div>
    </div>
  )
}
