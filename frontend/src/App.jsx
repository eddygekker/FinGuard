import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertIcon,
  BrainIcon,
  ChevronIcon,
  CopyIcon,
  DollarIcon,
  MoonIcon,
  RefreshIcon,
  SearchIcon,
  ShieldIcon,
  SparkIcon,
  SunIcon,
  TrendIcon,
  UsersIcon,
} from './Icons'
import './App.css'

function formatMrr(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

function riskClass(tier) {
  if (tier === 'high') return 'risk-high'
  if (tier === 'medium') return 'risk-medium'
  return 'risk-low'
}

function planClass(plan) {
  if (plan === 'Enterprise') return 'enterprise'
  if (plan === 'Pro') return 'pro'
  return ''
}

function statTone(key, value) {
  if (key === 'usage_drop_pct' && value >= 25) return 'warn'
  if (key === 'days_since_login' && value >= 14) return 'warn'
  if (key === 'open_tickets' && value >= 2) return 'warn'
  if (key === 'payment_failures' && value >= 1) return 'warn'
  return ''
}

const RISK_FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'high', label: 'High' },
  { id: 'medium', label: 'Medium' },
  { id: 'low', label: 'Low' },
]

const CUSTOMER_LIMIT = 50

const METRIC_TOOLTIPS = {
  active: 'Customers with an active subscription — still paying and not marked as churned.',
  highRisk: 'Accounts with a churn risk score of 65 or higher. These should be prioritized for retention outreach.',
  churnRate: 'Share of all customers who have cancelled. Calculated as churned ÷ total customers.',
  mrrAtRisk: 'Combined monthly subscription revenue from high-risk accounts only. This is the MRR you could lose if they churn.',
  rocAuc: 'Model accuracy score (0–1). Measures how well the ML model separates customers who churn from those who stay. Above 0.9 is strong.',
}

const SORTABLE_COLUMNS = [
  { id: 'company_name', label: 'Company' },
  { id: 'mrr', label: 'MRR', tooltip: 'Monthly Recurring Revenue — how much this customer pays per month in subscription fees.' },
  { id: 'risk_score', label: 'Risk', tooltip: 'Churn risk score (0–100) from the ML model. Higher score = more likely to cancel.' },
]

const COLUMN_TOOLTIPS = {
  plan: 'Subscription tier — Basic, Pro, or Enterprise. Higher tiers usually mean more revenue at stake.',
  signals: 'Health warning signs: usage drop %, open support tickets, and failed payments. More signals = higher churn risk.',
}

function sortIndicator(sortBy, sortDir, columnId) {
  if (sortBy !== columnId) return null
  return sortDir === 'asc' ? ' ↑' : ' ↓'
}

function HeaderTooltip({ text }) {
  return (
    <span className="header-tooltip">
      <button
        type="button"
        className="header-tooltip-trigger"
        aria-label={`About: ${text}`}
        onClick={(e) => e.stopPropagation()}
      >
        ?
      </button>
      <span className="header-tooltip-content header-tooltip-below" role="tooltip">
        {text}
      </span>
    </span>
  )
}

function MetricLabel({ label, tooltip }) {
  return (
    <p className="metric-label">
      <span>{label}</span>
      {tooltip && <HeaderTooltip text={tooltip} />}
    </p>
  )
}

function ColumnHeader({ label, tooltip, sortable, sortBy, sortDir, columnId, onSort }) {
  return (
    <div className="th-label">
      {sortable ? (
        <button
          type="button"
          className={`sort-header ${sortBy === columnId ? 'active' : ''}`}
          onClick={() => onSort(columnId)}
          aria-sort={
            sortBy === columnId
              ? sortDir === 'asc'
                ? 'ascending'
                : 'descending'
              : 'none'
          }
        >
          {label}
          {sortIndicator(sortBy, sortDir, columnId)}
        </button>
      ) : (
        <span className="col-label">{label}</span>
      )}
      {tooltip && <HeaderTooltip text={tooltip} />}
    </div>
  )
}

function SkeletonMetrics() {
  return (
    <>
      {[0, 1, 2, 3, 4].map((i) => (
        <div key={i} className="metric-card skeleton-card" style={{ animationDelay: `${i * 60}ms` }}>
          <div className="skeleton skeleton-label" />
          <div className="skeleton skeleton-value" />
        </div>
      ))}
    </>
  )
}

function SkeletonRows() {
  return (
    <>
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <tr key={i} className="skeleton-row">
          <td><div className="skeleton skeleton-cell wide" /></td>
          <td><div className="skeleton skeleton-cell narrow" /></td>
          <td><div className="skeleton skeleton-cell narrow" /></td>
          <td><div className="skeleton skeleton-cell narrow" /></td>
          <td><div className="skeleton skeleton-cell medium" /></td>
        </tr>
      ))}
    </>
  )
}

function RiskGauge({ score, tier }) {
  const radius = 28
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (Math.min(score, 100) / 100) * circumference

  return (
    <div className={`risk-gauge ${riskClass(tier)}`} role="img" aria-label={`Risk score ${Math.round(score)}, ${tier} tier`}>
      <svg viewBox="0 0 72 72" aria-hidden="true">
        <circle className="risk-gauge-track" cx="36" cy="36" r={radius} />
        <circle
          className="risk-gauge-fill"
          cx="36"
          cy="36"
          r={radius}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="risk-gauge-label">
        <strong>{Math.round(score)}</strong>
        <span>{tier}</span>
      </div>
    </div>
  )
}

function formatDriverLabel(signal) {
  if (!signal) return ''
  return signal.charAt(0).toUpperCase() + signal.slice(1)
}

function RiskDriversChart({ drivers, scoringMethod }) {
  if (!drivers?.length) return null

  const increasing = drivers.filter((d) => d.direction === 'increases risk')
  const shown = (increasing.length >= 3 ? increasing : drivers).slice(0, 5)
  const maxContribution = Math.max(...shown.map((d) => d.contribution), 0.001)

  return (
    <div className="drivers-block">
      <div className="drivers-header">
        <div>
          <h4 className="block-title">Top risk drivers</h4>
          <p className="drivers-hint">Longer bar = stronger impact on this customer&apos;s risk</p>
        </div>
        <span className="drivers-method">
          {scoringMethod === 'logistic_regression' ? 'ML model' : 'Rule-based'}
        </span>
      </div>
      <div className="drivers-chart">
        {shown.map((driver) => (
          <div key={driver.signal} className="driver-row">
            <span className="driver-label">{formatDriverLabel(driver.signal)}</span>
            <div className="driver-bar-track">
              <div
                className="driver-bar-fill"
                style={{ width: `${(driver.contribution / maxContribution) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function buildActionPlanText(analysis, companyName) {
  const lines = [
    `FinGuard Retention Plan — ${companyName}`,
    '',
    `Recommended: ${analysis.recommended_action}`,
    '',
  ]
  if (analysis.action_steps?.length) {
    lines.push('Action steps:')
    analysis.action_steps.forEach((step, i) => lines.push(`${i + 1}. ${step}`))
  }
  if (analysis.talking_points?.length) {
    lines.push('', 'Talking points:')
    analysis.talking_points.forEach((point) => lines.push(`• "${point}"`))
  }
  return lines.join('\n')
}

function RiskDistributionChart({ metrics }) {
  const high = metrics.high_risk_count || 0
  const medium = metrics.medium_risk_count || 0
  const low = metrics.low_risk_count || 0
  const total = high + medium + low || 1

  const segments = [
    { key: 'high', label: 'High', count: high, className: 'dist-high' },
    { key: 'medium', label: 'Medium', count: medium, className: 'dist-medium' },
    { key: 'low', label: 'Low', count: low, className: 'dist-low' },
  ]

  return (
    <section className="risk-distribution animate-in" aria-label="Risk distribution">
      <div className="risk-distribution-header">
        <h3>Risk distribution</h3>
        <p className="muted">{total} active accounts scored</p>
      </div>
      <div className="dist-bar" role="img" aria-label={`High ${high}, Medium ${medium}, Low ${low}`}>
        {segments.map((seg) => (
          seg.count > 0 && (
            <div
              key={seg.key}
              className={`dist-segment ${seg.className}`}
              style={{ width: `${(seg.count / total) * 100}%` }}
              title={`${seg.label}: ${seg.count}`}
            />
          )
        ))}
      </div>
      <div className="dist-legend">
        {segments.map((seg) => (
          <div key={seg.key} className="dist-legend-item">
            <span className={`dist-dot ${seg.className}`} />
            <span className="dist-legend-label">{seg.label}</span>
            <strong className="dist-legend-count">{seg.count}</strong>
            <span className="dist-legend-pct">{Math.round((seg.count / total) * 100)}%</span>
          </div>
        ))}
      </div>
    </section>
  )
}

function RiskBar({ score }) {
  return (
    <div className="risk-bar" aria-hidden="true">
      <div className="risk-bar-fill" style={{ width: `${Math.min(score, 100)}%` }} />
    </div>
  )
}

function App() {
  const [metrics, setMetrics] = useState(null)
  const [customers, setCustomers] = useState([])
  const [selected, setSelected] = useState(null)
  const [copilot, setCopilot] = useState(null)
  const [copilotLoading, setCopilotLoading] = useState(false)
  const [copilotError, setCopilotError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [tableLoading, setTableLoading] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastFetch, setLastFetch] = useState(null)
  const [riskFilter, setRiskFilter] = useState('all')
  const [refreshing, setRefreshing] = useState(false)
  const [copyFeedback, setCopyFeedback] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState('risk_score')
  const [sortDir, setSortDir] = useState('desc')
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'light'
    return localStorage.getItem('finguard-theme') === 'dark' ? 'dark' : 'light'
  })
  const riskFilterRef = useRef(riskFilter)
  riskFilterRef.current = riskFilter

  const loadDashboard = useCallback(async (selectFirst = false) => {
    const filter = riskFilterRef.current
    try {
      const customerQuery = filter === 'all'
        ? `?limit=${CUSTOMER_LIMIT}`
        : `?limit=${CUSTOMER_LIMIT}&risk=${filter}`
      const [metricsRes, customersRes] = await Promise.all([
        fetch('/api/metrics'),
        fetch(`/api/customers${customerQuery}`),
      ])

      if (!metricsRes.ok || !customersRes.ok) {
        throw new Error('API unavailable — run backend and init database')
      }

      setMetrics(await metricsRes.json())
      const rows = await customersRes.json()
      setCustomers(rows)
      setError(null)
      setLastFetch(new Date())

      if (selectFirst && rows.length > 0) {
        loadCustomer(rows[0].id, false)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  const loadCustomer = async (customerId, showLoader = true) => {
    if (showLoader) setDetailLoading(true)
    const res = await fetch(`/api/customers/${customerId}`)
    if (!res.ok) {
      setDetailLoading(false)
      return
    }
    setSelected(await res.json())
    setCopilot(null)
    setCopilotError(null)
    setCopyFeedback(false)
    setDetailLoading(false)
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await loadDashboard(false)
  }

  const handleFilterChange = async (filter) => {
    setRiskFilter(filter)
    setTableLoading(true)
    try {
      const query = filter === 'all'
        ? `?limit=${CUSTOMER_LIMIT}`
        : `?limit=${CUSTOMER_LIMIT}&risk=${filter}`
      const res = await fetch(`/api/customers${query}`)
      if (res.ok) {
        const rows = await res.json()
        setCustomers(rows)
        if (rows.length > 0) loadCustomer(rows[0].id, false)
        else {
          setSelected(null)
          setCopilot(null)
        }
      }
    } finally {
      setTableLoading(false)
    }
  }

  const analyzeWithCopilot = async () => {
    if (!selected) return
    setCopilotLoading(true)
    setCopilotError(null)

    try {
      const res = await fetch('/api/copilot/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_id: selected.id }),
      })

      const contentType = res.headers.get('content-type') || ''
      if (!contentType.includes('application/json')) {
        throw new Error('Backend returned an invalid response. Restart Flask with py run.py')
      }

      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Agent request failed')
      setCopilot(data)
      setCopyFeedback(false)
    } catch (err) {
      setCopilotError(err.message)
    } finally {
      setCopilotLoading(false)
    }
  }

  const copyActionPlan = async () => {
    const analysis = copilot?.analysis
    if (!analysis?.action_steps?.length || !selected) return

    try {
      await navigator.clipboard.writeText(buildActionPlanText(analysis, selected.company_name))
      setCopyFeedback(true)
      setTimeout(() => setCopyFeedback(false), 2000)
    } catch {
      setCopilotError('Could not copy to clipboard')
    }
  }

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('finguard-theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme((current) => (current === 'light' ? 'dark' : 'light'))
  }

  const handleSort = (columnId) => {
    if (sortBy === columnId) {
      setSortDir((dir) => (dir === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortBy(columnId)
    setSortDir(columnId === 'company_name' ? 'asc' : 'desc')
  }

  const displayedCustomers = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    let rows = query
      ? customers.filter((c) => c.company_name.toLowerCase().includes(query))
      : customers

    rows = [...rows].sort((a, b) => {
      let cmp = 0
      if (sortBy === 'company_name') {
        cmp = a.company_name.localeCompare(b.company_name)
      } else if (sortBy === 'mrr') {
        cmp = (a.mrr || 0) - (b.mrr || 0)
      } else {
        cmp = (a.risk_score || 0) - (b.risk_score || 0)
      }
      return sortDir === 'asc' ? cmp : -cmp
    })

    return rows
  }, [customers, searchQuery, sortBy, sortDir])

  useEffect(() => {
    loadDashboard(true)
  }, [])

  useEffect(() => {
    const interval = setInterval(() => loadDashboard(false), 30000)
    return () => clearInterval(interval)
  }, [loadDashboard])

  const statusLabel = error
    ? 'Offline'
    : metrics?.scoring_method === 'logistic_regression'
      ? 'ML Live'
      : 'Live'

  const urgencyClass = copilot?.analysis?.urgency?.toLowerCase() || ''

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <div className="brand-icon brand-logo">
              <img src="/logo.svg" alt="" width={40} height={40} />
            </div>
            <div>
              <p className="eyebrow">Retention Intelligence</p>
              <h1>FinGuard</h1>
            </div>
          </div>
          <div className="topbar-meta">
            <button
              type="button"
              className="theme-toggle"
              onClick={toggleTheme}
              aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
              title={theme === 'light' ? 'Dark mode' : 'Light mode'}
            >
              {theme === 'light' ? <MoonIcon size={16} /> : <SunIcon size={16} />}
            </button>
            <span className="status-pill">
              <span className={`status-dot ${error ? 'offline' : 'online'}`} />
              {statusLabel}
            </span>
            {lastFetch && (
              <time dateTime={lastFetch.toISOString()}>
                Updated {lastFetch.toLocaleTimeString()}
              </time>
            )}
          </div>
        </div>
      </header>

      <div className="main">
        <section className="page-intro animate-in">
          <h2 className="page-title">Churn command center</h2>
          <p className="page-subtitle">
            Monitor at-risk accounts, prioritize revenue impact, and get AI-powered retention playbooks.
          </p>
        </section>

        {error && (
          <div className="banner error animate-in" role="alert">
            {error}. Run <code>py backend/scripts/init_db.py</code> then{' '}
            <code>py backend/run.py</code>.
          </div>
        )}

        <section className="metrics-grid" aria-label="Key metrics">
          {loading ? (
            <SkeletonMetrics />
          ) : (
            metrics && (
              <>
                <article className="metric-card metric-blue animate-in" style={{ animationDelay: '40ms' }}>
                  <div className="metric-icon"><UsersIcon /></div>
                  <MetricLabel label="Active customers" tooltip={METRIC_TOOLTIPS.active} />
                  <h2 className="metric-value">{metrics.active_customers}</h2>
                  <p className="metric-hint">{metrics.churned_customers} churned total</p>
                </article>
                <article className="metric-card metric-red animate-in" style={{ animationDelay: '80ms' }}>
                  <div className="metric-icon"><AlertIcon /></div>
                  <MetricLabel label="High risk" tooltip={METRIC_TOOLTIPS.highRisk} />
                  <h2 className="metric-value">{metrics.high_risk_count}</h2>
                  <p className="metric-hint">{metrics.medium_risk_count} medium risk</p>
                </article>
                <article className="metric-card metric-amber animate-in" style={{ animationDelay: '120ms' }}>
                  <div className="metric-icon"><TrendIcon /></div>
                  <MetricLabel label="Churn rate" tooltip={METRIC_TOOLTIPS.churnRate} />
                  <h2 className="metric-value">{metrics.churn_rate_pct}%</h2>
                  <p className="metric-hint">Across all accounts</p>
                </article>
                <article className="metric-card accent animate-in" style={{ animationDelay: '160ms' }}>
                  <div className="metric-icon"><DollarIcon /></div>
                  <MetricLabel label="MRR at risk" tooltip={METRIC_TOOLTIPS.mrrAtRisk} />
                  <h2 className="metric-value">{formatMrr(metrics.mrr_at_risk)}</h2>
                  <p className="metric-hint">High-tier accounts only</p>
                </article>
                {metrics.model_roc_auc != null && (
                  <article className="metric-card metric-emerald animate-in" style={{ animationDelay: '200ms' }}>
                    <div className="metric-icon"><BrainIcon /></div>
                    <MetricLabel label="Model ROC-AUC" tooltip={METRIC_TOOLTIPS.rocAuc} />
                    <h2 className="metric-value">{metrics.model_roc_auc}</h2>
                    <p className="metric-hint">Logistic regression</p>
                  </article>
                )}
              </>
            )
          )}
        </section>

        {!loading && metrics && (
          <RiskDistributionChart metrics={metrics} />
        )}

        <main className="content-grid">
          <section className="panel animate-in" style={{ animationDelay: '180ms' }}>
            <div className="panel-header">
              <div>
                <h2>At-risk customers</h2>
                <p className="panel-desc">Search & sort · click a row for details</p>
              </div>
              <button
                type="button"
                className={`btn-secondary ${refreshing ? 'spinning' : ''}`}
                onClick={handleRefresh}
                disabled={refreshing}
              >
                <RefreshIcon />
                Refresh
              </button>
            </div>

            <div className="filter-bar" role="tablist" aria-label="Filter by risk tier">
              {RISK_FILTERS.map((filter) => (
                <button
                  key={filter.id}
                  type="button"
                  role="tab"
                  aria-selected={riskFilter === filter.id}
                  className={`filter-pill ${riskFilter === filter.id ? 'active' : ''}`}
                  onClick={() => handleFilterChange(filter.id)}
                >
                  {filter.label}
                </button>
              ))}
            </div>

            <div className="table-toolbar">
              <div className="search-field">
                <SearchIcon size={15} />
                <input
                  type="search"
                  placeholder="Search company…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  aria-label="Search companies"
                />
              </div>
              <span className="table-count">
                {displayedCustomers.length} of {customers.length} shown
              </span>
            </div>

            <div className="panel-body table-wrap">
              <table>
                <thead>
                  <tr>
                    {SORTABLE_COLUMNS.map((col) => (
                      <th key={col.id}>
                        <ColumnHeader
                          label={col.label}
                          tooltip={col.tooltip}
                          sortable
                          sortBy={sortBy}
                          sortDir={sortDir}
                          columnId={col.id}
                          onSort={handleSort}
                        />
                      </th>
                    ))}
                    <th>
                      <ColumnHeader label="Plan" tooltip={COLUMN_TOOLTIPS.plan} />
                    </th>
                    <th>
                      <ColumnHeader label="Signals" tooltip={COLUMN_TOOLTIPS.signals} />
                    </th>
                    <th aria-hidden="true" />
                  </tr>
                </thead>
                <tbody>
                  {tableLoading ? (
                    <SkeletonRows />
                  ) : displayedCustomers.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="table-empty">
                        {searchQuery.trim()
                          ? `No companies match "${searchQuery.trim()}".`
                          : 'No customers match this filter.'}
                      </td>
                    </tr>
                  ) : (
                    displayedCustomers.map((customer) => (
                      <tr
                        key={customer.id}
                        className={selected?.id === customer.id ? 'selected' : ''}
                        onClick={() => loadCustomer(customer.id)}
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            loadCustomer(customer.id)
                          }
                        }}
                      >
                        <td className="company-cell">{customer.company_name}</td>
                        <td className="tabular">{formatMrr(customer.mrr)}</td>
                        <td>
                          <div className="risk-cell">
                            <span className={`badge ${riskClass(customer.risk_tier)}`}>
                              {Math.round(customer.risk_score)}
                            </span>
                            <RiskBar score={customer.risk_score} />
                          </div>
                        </td>
                        <td>
                          <span className={`plan-badge ${planClass(customer.plan)}`}>
                            {customer.plan}
                          </span>
                        </td>
                        <td>
                          <div className="signal-chips">
                            {customer.usage_drop_pct > 0 && (
                              <span className="signal-chip warn">↓{customer.usage_drop_pct}% usage</span>
                            )}
                            {customer.open_tickets > 0 && (
                              <span className="signal-chip">{customer.open_tickets} tickets</span>
                            )}
                            {customer.payment_failures > 0 && (
                              <span className="signal-chip danger">Payment fail</span>
                            )}
                          </div>
                        </td>
                        <td className="row-chevron" aria-hidden="true">
                          <ChevronIcon />
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel panel-detail animate-in" style={{ animationDelay: '220ms' }}>
            <div className="panel-header">
              <div>
                <h2>Customer 360</h2>
                <p className="panel-desc">
                  {selected ? 'Risk profile & retention agent' : 'Select an account to inspect'}
                </p>
              </div>
            </div>

            <div className="panel-body padded">
              {detailLoading ? (
                <div className="detail-skeleton">
                  <div className="skeleton skeleton-hero" />
                  <div className="detail-grid">
                    {[0, 1, 2, 3, 4, 5].map((i) => (
                      <div key={i} className="skeleton skeleton-tile" />
                    ))}
                  </div>
                </div>
              ) : selected ? (
                <div className="detail">
                  <div className="detail-hero">
                    <div className="detail-identity">
                      <h3>{selected.company_name}</h3>
                      <p className="muted">{selected.industry}</p>
                      <a className="detail-email" href={`mailto:${selected.email}`}>
                        {selected.email}
                      </a>
                    </div>
                    <RiskGauge score={selected.risk_score} tier={selected.risk_tier} />
                  </div>

                  <div className="detail-grid">
                    {[
                      ['MRR', formatMrr(selected.mrr), 'mrr'],
                      ['Plan', selected.plan, 'plan'],
                      ['Usage drop', `${selected.usage_drop_pct}%`, 'usage_drop_pct', selected.usage_drop_pct],
                      ['Days since login', selected.days_since_login, 'days_since_login', selected.days_since_login],
                      ['Open tickets', selected.open_tickets, 'open_tickets', selected.open_tickets],
                      ['Payment failures', selected.payment_failures, 'payment_failures', selected.payment_failures],
                    ].map(([label, value, key, raw]) => (
                      <div key={key} className={`stat-tile ${statTone(key, raw ?? value)}`}>
                        <span>{label}</span>
                        <strong>{value}</strong>
                      </div>
                    ))}
                  </div>

                  <RiskDriversChart
                    drivers={selected.risk_drivers}
                    scoringMethod={selected.scoring_method}
                  />

                  {selected.open_support_tickets?.length > 0 && (
                    <div className="tickets-block">
                      <h4 className="block-title">Open support tickets</h4>
                      <ul className="ticket-list">
                        {selected.open_support_tickets.map((ticket) => (
                          <li key={ticket.id}>
                            <span className={`ticket-priority ${ticket.priority}`}>{ticket.priority}</span>
                            <span className="ticket-subject">{ticket.subject}</span>
                            <span className="ticket-date">{ticket.created_at}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="copilot-panel">
                    <div className="copilot-header">
                      <div className="copilot-title-row">
                        <span className="copilot-icon"><SparkIcon size={18} /></span>
                        <div>
                          <p className="eyebrow">Retention Agent</p>
                          <p className="muted">
                            {copilot?.provider
                              ? `Powered by ${copilot.provider}`
                              : 'AI retention expert · one-click analysis'}
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        className="btn-primary"
                        onClick={analyzeWithCopilot}
                        disabled={copilotLoading}
                      >
                        <SparkIcon size={14} />
                        {copilotLoading ? 'Analyzing…' : 'Ask Agent'}
                      </button>
                    </div>

                    {copilotLoading && (
                      <div className="copilot-loading" aria-live="polite">
                        <div className="copilot-loading-dots">
                          <span /><span /><span />
                        </div>
                        <p>Reviewing risk signals and building a retention plan…</p>
                      </div>
                    )}

                    {copilotError && (
                      <div className="copilot-error" role="alert">{copilotError}</div>
                    )}

                    {copilot?.analysis && !copilotLoading && (
                      <div className="copilot-result">
                        {copilot.analysis.urgency && (
                          <div className={`urgency-banner ${urgencyClass}`} role="status">
                            <AlertIcon size={22} />
                            <div className="urgency-banner-text">
                              <strong>{copilot.analysis.urgency} urgency</strong>
                              <span>Prioritize retention outreach for this account</span>
                            </div>
                          </div>
                        )}

                        <div className="copilot-section">
                          <h4>Summary</h4>
                          <p>{copilot.analysis.summary}</p>
                        </div>

                        {copilot.analysis.why_at_risk?.length > 0 && (
                          <div className="copilot-section">
                            <h4>Why at risk</h4>
                            <ul>
                              {copilot.analysis.why_at_risk.map((item) => (
                                <li key={item}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        <div className="copilot-section copilot-action">
                          <h4>Recommended action</h4>
                          <p>{copilot.analysis.recommended_action}</p>
                        </div>

                        {copilot.analysis.action_steps?.length > 0 && (
                          <div className="copilot-section">
                            <div className="action-plan-header">
                              <h4>Action plan</h4>
                              <button
                                type="button"
                                className={`btn-copy ${copyFeedback ? 'copied' : ''}`}
                                onClick={copyActionPlan}
                              >
                                <CopyIcon />
                                {copyFeedback ? 'Copied!' : 'Copy action plan'}
                              </button>
                            </div>
                            <ol className="action-steps">
                              {copilot.analysis.action_steps.map((item, i) => (
                                <li key={item}>
                                  <span className="step-num">{i + 1}</span>
                                  <span>{item}</span>
                                </li>
                              ))}
                            </ol>
                          </div>
                        )}

                        {copilot.analysis.talking_points?.length > 0 && (
                          <div className="copilot-section talking-points">
                            <h4>Talking points</h4>
                            <ul>
                              {copilot.analysis.talking_points.map((item) => (
                                <li key={item}>&ldquo;{item}&rdquo;</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {copilot.analysis.confidence_note && (
                          <p className="confidence-note">{copilot.analysis.confidence_note}</p>
                        )}
                      </div>
                    )}

                    {!copilot && !copilotLoading && !copilotError && (
                      <div className="copilot-empty">
                        <p>Get a tailored retention playbook with specific next steps and call scripts.</p>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="empty-state">
                  <div className="empty-illustration">
                    <ShieldIcon size={32} />
                  </div>
                  <h3>Pick an account</h3>
                  <p>Select a customer from the table to view their risk profile and run the Retention Agent.</p>
                </div>
              )}
            </div>
          </section>
        </main>
      </div>
    </div>
  )
}

export default App
