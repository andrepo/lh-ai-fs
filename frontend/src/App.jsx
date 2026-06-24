import { useState, useEffect } from 'react'

function App() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('all')
  const [expandedId, setExpandedId] = useState(null)
  const [progressText, setProgressText] = useState('')

  // Simulate progress step messages during backend processing
  useEffect(() => {
    let timer
    if (loading) {
      const steps = [
        { time: 0, text: 'Scanning Motion for Summary Judgment...' },
        { time: 3000, text: 'Extracting citations, statements, and footnotes...' },
        { time: 6000, text: 'Fact-checking worksite claims against source documents...' },
        { time: 10000, text: 'Verifying case holdings and direct quote accuracy...' },
        { time: 14000, text: 'Running LangChain orchestrator to synthesize memo and score briefs...' },
        { time: 18000, text: 'Finalizing executive legal report...' },
      ]

      steps.forEach((step) => {
        timer = setTimeout(() => {
          setProgressText(step.text)
        }, step.time)
      })
    } else {
      setProgressText('')
    }
    return () => clearTimeout(timer)
  }, [loading])

  const runAnalysis = async () => {
    setLoading(true)
    setError(null)
    setReport(null)

    // Try port 8000 (uvicorn dev server) first, fallback to 8002 (docker container)
    const endpoints = [
      'http://localhost:8000/analyze',
      'http://localhost:8002/analyze'
    ]

    let response = null
    let lastError = null

    for (const url of endpoints) {
      try {
        response = await fetch(url, {
          method: 'POST',
        })
        if (response.ok) {
          break;
        }
      } catch (err) {
        lastError = err;
      }
    }

    if (response && response.ok) {
      try {
        const data = await response.json()
        setReport(data.report)
      } catch (err) {
        setError('Failed to parse analysis results.')
      } finally {
        setLoading(false)
      }
    } else {
      setError(
        lastError 
          ? `Could not connect to backend. Please ensure the development server is running. (Error: ${lastError.message})` 
          : 'Server returned an error response.'
      )
      setLoading(false)
    }
  }

  // Count summary metrics
  const getMetrics = () => {
    if (!report || !report.findings) return { high: 0, medium: 0, low: 0, total: 0 }
    return report.findings.reduce((acc, curr) => {
      const severity = (curr.severity || 'low').toLowerCase()
      acc[severity] = (acc[severity] || 0) + 1
      acc.total += 1
      return acc
    }, { high: 0, medium: 0, low: 0, total: 0 })
  }

  const metrics = getMetrics()

  // Filtered findings list
  const getFilteredFindings = () => {
    if (!report || !report.findings) return []
    return report.findings.filter((f) => {
      if (activeTab === 'all') return true
      if (activeTab === 'factual') return f.category === 'factual_assertion'
      if (activeTab === 'legal') return f.category === 'legal_citation'
      if (activeTab === 'flaws') return f.status === 'fabricated' || f.status === 'contradicted' || f.status === 'mischaracterized'
      return true
    })
  }

  const filteredFindings = getFilteredFindings()

  const getStatusColor = (status) => {
    const s = (status || '').toLowerCase()
    if (s === 'supported') return '#10b981' // emerald
    if (s === 'contradicted' || s === 'fabricated') return '#ef4444' // red
    if (s === 'mischaracterized') return '#f59e0b' // amber
    return '#64748b' // slate
  }

  const getSeverityColor = (severity) => {
    const s = (severity || '').toLowerCase()
    if (s === 'high') return '#ef4444'
    if (s === 'medium') return '#f59e0b'
    return '#3b82f6' // blue
  }

  return (
    <div className="app-container">
      {/* Global CSS Inject */}
      <style>{`
        :root {
          color-scheme: dark;
        }
        body {
          margin: 0;
          padding: 0;
          background-color: #0b0f19;
          background-image: 
            radial-gradient(at 0% 0%, rgba(31, 41, 234, 0.15) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(99, 102, 241, 0.1) 0px, transparent 50%);
          color: #f1f5f9;
          font-family: 'Outfit', 'Inter', system-ui, -apple-system, sans-serif;
          -webkit-font-smoothing: antialiased;
        }
        .app-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 40px 20px;
        }
        
        /* Header styles */
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 40px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          padding-bottom: 24px;
        }
        .logo-section h1 {
          font-size: 2.2rem;
          font-weight: 800;
          margin: 0;
          background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          letter-spacing: -0.025em;
        }
        .logo-section p {
          margin: 4px 0 0 0;
          color: #94a3b8;
          font-size: 1rem;
        }
        
        /* Premium Buttons */
        .btn-primary {
          background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
          color: white;
          border: none;
          padding: 14px 32px;
          border-radius: 12px;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
          display: inline-flex;
          align-items: center;
          gap: 10px;
        }
        .btn-primary:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 8px 30px rgba(99, 102, 241, 0.6);
        }
        .btn-primary:active:not(:disabled) {
          transform: translateY(0);
        }
        .btn-primary:disabled {
          background: #334155;
          color: #94a3b8;
          box-shadow: none;
          cursor: not-allowed;
        }
        .btn-secondary {
          background: rgba(255, 255, 255, 0.05);
          color: #cbd5e1;
          border: 1px solid rgba(255, 255, 255, 0.1);
          padding: 10px 20px;
          border-radius: 10px;
          font-size: 0.95rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          display: inline-flex;
          align-items: center;
          gap: 8px;
        }
        .btn-secondary:hover:not(:disabled) {
          background: rgba(255, 255, 255, 0.1);
          border-color: rgba(255, 255, 255, 0.2);
          color: white;
        }
        .btn-secondary:active:not(:disabled) {
          transform: scale(0.98);
        }
        .btn-secondary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        
        /* Loading States */
        .loading-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 80px 40px;
          background: rgba(30, 41, 59, 0.4);
          border-radius: 24px;
          border: 1px solid rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(10px);
          margin-top: 20px;
        }
        .spinner {
          width: 60px;
          height: 60px;
          border: 5px solid rgba(99, 102, 241, 0.1);
          border-top-color: #6366f1;
          border-radius: 50%;
          animation: spin 1s infinite linear;
          margin-bottom: 24px;
        }
        .pulse-text {
          font-size: 1.1rem;
          color: #cbd5e1;
          animation: pulse 2s infinite ease-in-out;
          font-weight: 500;
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 1; }
        }
        
        /* Error Alert */
        .error-card {
          background: rgba(220, 38, 38, 0.1);
          border: 1px solid rgba(220, 38, 38, 0.3);
          border-radius: 16px;
          padding: 20px;
          color: #fca5a5;
          margin-top: 20px;
        }
        
        /* Grid Layout for dashboard */
        .dashboard-grid {
          display: grid;
          grid-template-columns: 350px 1fr;
          gap: 30px;
          margin-top: 20px;
        }
        @media (max-width: 900px) {
          .dashboard-grid {
            grid-template-columns: 1fr;
          }
        }
        
        /* Summary / Score Card */
        .sidebar {
          display: flex;
          flex-direction: column;
          gap: 30px;
        }
        .card {
          background: rgba(30, 41, 59, 0.45);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 20px;
          padding: 24px;
          backdrop-filter: blur(16px);
          transition: border-color 0.3s ease;
        }
        .card:hover {
          border-color: rgba(255, 255, 255, 0.12);
        }
        
        /* Confidence Dial */
        .confidence-section {
          text-align: center;
        }
        .score-circle {
          position: relative;
          width: 160px;
          height: 160px;
          margin: 0 auto 20px auto;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .score-circle svg {
          transform: rotate(-90deg);
        }
        .score-circle .number {
          position: absolute;
          font-size: 2.2rem;
          font-weight: 800;
          color: white;
        }
        .confidence-label {
          font-weight: 700;
          font-size: 1.2rem;
          margin-bottom: 8px;
        }
        .confidence-desc {
          font-size: 0.85rem;
          color: #94a3b8;
          line-height: 1.4;
        }
        
        /* Metrics Counters */
        .metrics-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }
        .metric-mini-card {
          background: rgba(15, 23, 42, 0.4);
          border: 1px solid rgba(255, 255, 255, 0.04);
          border-radius: 12px;
          padding: 14px;
          text-align: center;
        }
        .metric-mini-card.high-flaw {
          border-left: 3px solid #ef4444;
        }
        .metric-mini-card.med-flaw {
          border-left: 3px solid #f59e0b;
        }
        .metric-val {
          font-size: 1.8rem;
          font-weight: 800;
          color: white;
          margin-bottom: 4px;
        }
        .metric-lbl {
          font-size: 0.75rem;
          color: #94a3b8;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        
        /* Judicial Memo Formats */
        .memo-title {
          font-size: 0.85rem;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          color: #818cf8;
          margin-bottom: 12px;
          font-weight: 700;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .memo-content {
          font-family: 'Georgia', serif;
          font-size: 1.05rem;
          color: #e2e8f0;
          line-height: 1.7;
          border-left: 2px solid #6366f1;
          padding-left: 18px;
          font-style: italic;
          margin: 0;
        }
        
        /* Tabs styles */
        .tabs-header {
          display: flex;
          background: rgba(15, 23, 42, 0.6);
          border-radius: 12px;
          padding: 4px;
          margin-bottom: 24px;
          border: 1px solid rgba(255, 255, 255, 0.04);
          gap: 4px;
          overflow-x: auto;
        }
        .tab-btn {
          flex: 1;
          background: transparent;
          border: none;
          color: #94a3b8;
          padding: 10px 16px;
          border-radius: 8px;
          font-size: 0.9rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          white-space: nowrap;
        }
        .tab-btn:hover {
          color: white;
          background: rgba(255, 255, 255, 0.03);
        }
        .tab-btn.active {
          color: white;
          background: #312e81;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.1);
        }
        
        /* Findings list */
        .findings-list {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .finding-card {
          background: rgba(30, 41, 59, 0.3);
          border: 1px solid rgba(255, 255, 255, 0.05);
          border-radius: 16px;
          overflow: hidden;
          transition: all 0.2s ease;
        }
        .finding-card:hover {
          border-color: rgba(99, 102, 241, 0.3);
          background: rgba(30, 41, 59, 0.45);
        }
        .finding-card-header {
          padding: 20px;
          cursor: pointer;
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 16px;
        }
        .finding-card-main {
          flex: 1;
        }
        .finding-statement {
          font-size: 1.05rem;
          font-weight: 600;
          color: white;
          line-height: 1.4;
          margin-bottom: 8px;
        }
        .finding-meta {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 10px;
          font-size: 0.8rem;
          color: #94a3b8;
        }
        .badge {
          padding: 4px 8px;
          border-radius: 6px;
          font-weight: 700;
          text-transform: uppercase;
          font-size: 0.7rem;
          letter-spacing: 0.05em;
        }
        .badge-category {
          background: rgba(99, 102, 241, 0.15);
          color: #818cf8;
          border: 1px solid rgba(99, 102, 241, 0.3);
        }
        .badge-severity {
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .finding-card-body {
          border-top: 1px solid rgba(255, 255, 255, 0.05);
          padding: 20px;
          background: rgba(15, 23, 42, 0.3);
        }
        
        .chevron-icon {
          transition: transform 0.2s ease;
          color: #64748b;
        }
        .finding-card.expanded .chevron-icon {
          transform: rotate(180deg);
        }
        
        /* Expandable Table / Comparison View */
        .comparison-table {
          width: 100%;
          border-collapse: collapse;
          margin-bottom: 16px;
          font-size: 0.95rem;
        }
        .comparison-table td {
          padding: 12px;
          vertical-align: top;
          border-bottom: 1px solid rgba(255, 255, 255, 0.03);
        }
        .comparison-table tr:last-child td {
          border-bottom: none;
        }
        .table-label {
          font-weight: 700;
          color: #94a3b8;
          width: 180px;
          text-transform: uppercase;
          font-size: 0.75rem;
          letter-spacing: 0.05em;
        }
        .quote-block {
          font-family: 'Georgia', serif;
          font-style: italic;
          border-left: 2px solid #ef4444;
          padding-left: 12px;
          color: #cbd5e1;
          margin: 4px 0;
        }
        .evidence-block {
          border-left: 2px solid #10b981;
          padding-left: 12px;
          color: #cbd5e1;
          margin: 4px 0;
        }
        .explanation-text {
          color: #cbd5e1;
          line-height: 1.5;
        }
        
        /* empty state */
        .empty-state {
          text-align: center;
          padding: 60px 20px;
          color: #64748b;
        }
        .empty-state p {
          margin-bottom: 24px;
        }
      `}</style>

      {/* Top Header */}
      <header className="header">
        <div className="logo-section">
          <h1>BS Detector</h1>
          <p>Multi-Agent Legal Verification Dashboard (LangChain Orchestrated)</p>
        </div>
        {report !== null && (
          <button
            className="btn-secondary"
            onClick={runAnalysis}
            disabled={loading}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
            </svg>
            Re-run Verification
          </button>
        )}
      </header>

      {/* Loading Progress State */}
      {loading && (
        <div className="loading-container">
          <div className="spinner"></div>
          <div className="pulse-text">{progressText}</div>
          <p style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '12px' }}>
            LangChain is routing parallel tasks and executing verifiers. This takes approximately 15-20 seconds.
          </p>
        </div>
      )}

      {/* Error Card */}
      {error && (
        <div className="error-card">
          <h3 style={{ margin: '0 0 8px 0', fontSize: '1.1rem' }}>Orchestrator Execution Error</h3>
          <p style={{ margin: 0, fontSize: '0.95rem' }}>{error}</p>
        </div>
      )}

      {/* Empty State before load */}
      {report === null && !loading && !error && (
        <div className="empty-state">
          <svg style={{ marginBottom: '16px', opacity: 0.3 }} width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
          <h3>Ready for LangChain Scan</h3>
          <p>Click below to start the multi-agent legal verifier and generate the overall brief integrity score.</p>
          <button className="btn-primary" onClick={runAnalysis}>
            Start Analysis
          </button>
        </div>
      )}

      {/* Dashboard View */}
      {report && (
        <div className="dashboard-grid">
          {/* Sidebar Panel */}
          <div className="sidebar">
            {/* Reliability / Confidence score */}
            <div className="card confidence-section">
              <h3 className="confidence-label">Brief Integrity Rating</h3>
              <div className="score-circle">
                <svg width="160" height="160">
                  <circle
                    cx="80"
                    cy="80"
                    r="70"
                    fill="transparent"
                    stroke="rgba(255,255,255,0.05)"
                    strokeWidth="10"
                  />
                  <circle
                    cx="80"
                    cy="80"
                    r="70"
                    fill="transparent"
                    stroke={
                      report.overall_confidence > 0.7 
                        ? '#10b981' 
                        : report.overall_confidence > 0.4 
                          ? '#f59e0b' 
                          : '#ef4444'
                    }
                    strokeWidth="10"
                    strokeDasharray={440}
                    strokeDashoffset={440 - (440 * (report.overall_confidence || 0))}
                    strokeLinecap="round"
                    style={{ transition: 'stroke-dashoffset 1.5s ease-out' }}
                  />
                </svg>
                <div className="number">
                  {Math.round((report.overall_confidence || 0) * 100)}%
                </div>
              </div>
              <p className="confidence-desc">
                {report.overall_confidence > 0.7 
                  ? 'High brief integrity. Precedents are correctly cited and worksite facts match internal primary records.'
                  : report.overall_confidence > 0.4
                    ? 'Caution advised. Found significant legal mischaracterizations or missing citations in critical areas.'
                    : 'Critical alerts triggered. Brief contains fabricated case citations and facts that are directly contradicted by site logs.'
                }
              </p>
            </div>

            {/* Metrics Counter Card */}
            <div className="card">
              <h3 style={{ margin: '0 0 16px 0', fontSize: '1rem', color: '#94a3b8' }}>Pipeline Verification Metrics</h3>
              <div className="metrics-grid">
                <div className="metric-mini-card high-flaw">
                  <div className="metric-val">{metrics.high}</div>
                  <div className="metric-lbl">High Severity</div>
                </div>
                <div className="metric-mini-card med-flaw">
                  <div className="metric-val">{metrics.medium}</div>
                  <div className="metric-lbl">Medium Sev</div>
                </div>
                <div className="metric-mini-card">
                  <div className="metric-val">{metrics.low}</div>
                  <div className="metric-lbl">Low / Clear</div>
                </div>
                <div className="metric-mini-card">
                  <div className="metric-val">{metrics.total}</div>
                  <div className="metric-lbl">Total Scanned</div>
                </div>
              </div>
            </div>
          </div>

          {/* Main Dashboard Panel */}
          <div className="main-panel">
            {/* Judicial Memo */}
            <div className="card" style={{ marginBottom: '30px' }}>
              <div className="memo-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                Judicial Memo Draft
              </div>
              <p className="memo-content">
                "{report.summary || 'Judicial synthesizer report summary not available.'}"
              </p>
            </div>

            {/* Findings Section */}
            <div>
              {/* Tab Filters */}
              <div className="tabs-header">
                <button
                  className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`}
                  onClick={() => setActiveTab('all')}
                >
                  All ({report.findings?.length || 0})
                </button>
                <button
                  className={`tab-btn ${activeTab === 'flaws' ? 'active' : ''}`}
                  onClick={() => setActiveTab('flaws')}
                  style={{ color: metrics.high + metrics.medium > 0 ? '#fca5a5' : '#94a3b8' }}
                >
                  Flaws ({metrics.high + metrics.medium})
                </button>
                <button
                  className={`tab-btn ${activeTab === 'factual' ? 'active' : ''}`}
                  onClick={() => setActiveTab('factual')}
                >
                  Factual Claims
                </button>
                <button
                  className={`tab-btn ${activeTab === 'legal' ? 'active' : ''}`}
                  onClick={() => setActiveTab('legal')}
                >
                  Precedents & Law
                </button>
              </div>

              {/* Cards List */}
              <div className="findings-list">
                {filteredFindings.map((finding) => {
                  const isExpanded = expandedId === finding.id
                  const isFactual = finding.category === 'factual_assertion'
                  
                  return (
                    <div 
                      key={finding.id} 
                      className={`finding-card ${isExpanded ? 'expanded' : ''}`}
                    >
                      {/* Card Header Toggle */}
                      <div 
                        className="finding-card-header"
                        onClick={() => setExpandedId(isExpanded ? null : finding.id)}
                      >
                        <div className="finding-card-main">
                          <div className="finding-statement">
                            {finding.statement}
                          </div>
                          <div className="finding-meta">
                            <span className="badge badge-category">
                              {isFactual ? 'Factual Claim' : 'Legal Cit.'}
                            </span>
                            <span 
                              className="badge" 
                              style={{ 
                                background: `${getStatusColor(finding.status)}20`, 
                                color: getStatusColor(finding.status),
                                border: `1px solid ${getStatusColor(finding.status)}40`
                              }}
                            >
                              {finding.status}
                            </span>
                            <span 
                              className="badge badge-severity"
                              style={{ color: getSeverityColor(finding.severity) }}
                            >
                              Sev: {finding.severity}
                            </span>
                            {finding.id && <span>ID: {finding.id}</span>}
                          </div>
                        </div>
                        <div className="chevron-icon">
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <polyline points="6 9 12 15 18 9" />
                          </svg>
                        </div>
                      </div>

                      {/* Card Expandable Details Body */}
                      {isExpanded && (
                        <div className="finding-card-body">
                          <table className="comparison-table">
                            <tbody>
                              {!isFactual && finding.details?.citation_target && (
                                <tr>
                                  <td className="table-label">Precedent Authority</td>
                                  <td style={{ color: '#fff', fontWeight: 600 }}>{finding.details.citation_target}</td>
                                </tr>
                              )}
                              
                              {!isFactual && finding.details?.actual_holding && (
                                <tr>
                                  <td className="table-label">Actual Case Law Holding</td>
                                  <td className="explanation-text">{finding.details.actual_holding}</td>
                                </tr>
                              )}

                              {isFactual && finding.details?.source_file && (
                                <tr>
                                  <td className="table-label">Source Document</td>
                                  <td style={{ color: '#fff' }}>{finding.details.source_file}</td>
                                </tr>
                              )}

                              {isFactual && finding.details?.evidence && (
                                <tr>
                                  <td className="table-label">Evidence in File</td>
                                  <td>
                                    <div className="evidence-block">
                                      "{finding.details.evidence}"
                                    </div>
                                  </td>
                                </tr>
                              )}

                              {!isFactual && finding.statement && (
                                <tr>
                                  <td className="table-label">Claimed Quote Accuracy</td>
                                  <td>
                                    <span style={{ 
                                      color: finding.details?.quote_accuracy === 'accurate' ? '#10b981' : '#f59e0b',
                                      fontWeight: 700,
                                      textTransform: 'uppercase',
                                      fontSize: '0.85rem'
                                    }}>
                                      {finding.details?.quote_accuracy || 'N/A'}
                                    </span>
                                  </td>
                                </tr>
                              )}

                              {/* Confidence Layer */}
                              <tr>
                                <td className="table-label">Verifier Confidence</td>
                                <td>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                    <span style={{ fontWeight: 800, color: finding.confidence >= 0.8 ? '#10b981' : finding.confidence >= 0.5 ? '#f59e0b' : '#ef4444' }}>
                                      {Math.round((finding.confidence || 0) * 100)}%
                                    </span>
                                    <div style={{ height: '6px', width: '100px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden' }}>
                                      <div style={{ height: '100%', width: `${(finding.confidence || 0) * 100}%`, background: finding.confidence >= 0.8 ? '#10b981' : finding.confidence >= 0.5 ? '#f59e0b' : '#ef4444' }} />
                                    </div>
                                  </div>
                                  <div style={{ fontSize: '0.85rem', color: '#94a3b8', fontStyle: 'italic' }}>
                                    {finding.confidence_explanation || 'Confidence score calculated by verification agent.'}
                                  </div>
                                </td>
                              </tr>

                              <tr>
                                <td className="table-label">Verification Finding Rationale</td>
                                <td className="explanation-text">{finding.explanation}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )
                })}

                {filteredFindings.length === 0 && (
                  <div style={{ textAlign: 'center', padding: '40px', color: '#64748b' }}>
                    No findings matches this filter.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
