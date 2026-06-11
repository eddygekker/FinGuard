import { useCallback, useEffect, useState } from 'react'
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

function App() {
  const [metrics, setMetrics] = useState(null)
  const [customers, setCustomers] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastFetch, setLastFetch] = useState(null)

  const loadDashboard = useCallback(async () => {
    try {
      const [metricsRes, customersRes] = await Promise.all([
        fetch('/api/metrics'),
        fetch('/api/customers?limit=10'),
      ])

      if (!metricsRes.ok || !customersRes.ok) {
        throw new Error('API unavailable — run backend and init database')
      }

      const metricsData = await metricsRes.json()
      const customersData = await customersRes.json()

      setMetrics(metricsData)
      setCustomers(customersData)
      setError(null)
      setLastFetch(new Date())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadCustomer = async (customerId) => {
    const res = await fetch(`/api/customers/${customerId}`)
    if (!res.ok) return
    setSelected(await res.json())
  }

  useEffect(() => {
    loadDashboard()
    const interval = setInterval(loadDashboard, 30000)
    return () => clearInterval(interval)
  }, [loadDashboard])

  return (
    <div className="app">
      <header className="header">
        <div>
          <p className="eyebrow">Retention Intelligence</p>
          <h1>FinGuard</h1>
        </div>
        <div className="header-meta">
          <span className={`status-dot ${error ? 'offline' : 'online'}`} />
          {error ? 'API offline' : 'Live dashboard'}
          {lastFetch && (
            <span className="muted">
              Updated {lastFetch.toLocaleTimeString()}
            </span>
          )}
        </div>
      </header>

      {error && (
        <div className="banner error">
          {error}. From project root run: <code>py backend/scripts/init_db.py</code>
          then start Flask with <code>py backend/run.py</code>.
        </div>
      )}

      <section className="metrics-grid">
        {loading ? (
          <p className="muted">Loading metrics...</p>
        ) : (
          metrics && (
            <>
              <article className="metric-card">
                <p>Active customers</p>
                <h2>{metrics.active_customers}</h2>
              </article>
              <article className="metric-card">
                <p>High risk</p>
                <h2>{metrics.high_risk_count}</h2>
              </article>
              <article className="metric-card">
                <p>Churn rate</p>
                <h2>{metrics.churn_rate_pct}%</h2>
              </article>
              <article className="metric-card accent">
                <p>MRR at risk</p>
                <h2>{formatMrr(metrics.mrr_at_risk)}</h2>
              </article>
            </>
          )
        )}
      </section>

      <main className="content-grid">
        <section className="panel">
          <div className="panel-header">
            <h2>Top at-risk customers</h2>
            <button type="button" onClick={loadDashboard}>
              Refresh
            </button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Plan</th>
                  <th>MRR</th>
                  <th>Risk</th>
                  <th>Signals</th>
                </tr>
              </thead>
              <tbody>
                {customers.map((customer) => (
                  <tr
                    key={customer.id}
                    className={selected?.id === customer.id ? 'selected' : ''}
                    onClick={() => loadCustomer(customer.id)}
                  >
                    <td>{customer.company_name}</td>
                    <td>{customer.plan}</td>
                    <td>{formatMrr(customer.mrr)}</td>
                    <td>
                      <span className={`badge ${riskClass(customer.risk_tier)}`}>
                        {customer.risk_score}
                      </span>
                    </td>
                    <td className="signals">
                      {customer.usage_drop_pct}% usage drop · {customer.open_tickets} tickets
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>Customer detail</h2>
          </div>
          {selected ? (
            <div className="detail">
              <h3>{selected.company_name}</h3>
              <p className="muted">{selected.industry} · {selected.plan}</p>
              <div className="detail-grid">
                <div>
                  <span>Risk score</span>
                  <strong className={riskClass(selected.risk_tier)}>
                    {selected.risk_score} ({selected.risk_tier})
                  </strong>
                </div>
                <div>
                  <span>MRR</span>
                  <strong>{formatMrr(selected.mrr)}</strong>
                </div>
                <div>
                  <span>Usage drop</span>
                  <strong>{selected.usage_drop_pct}%</strong>
                </div>
                <div>
                  <span>Days since login</span>
                  <strong>{selected.days_since_login}</strong>
                </div>
                <div>
                  <span>Open tickets</span>
                  <strong>{selected.open_tickets}</strong>
                </div>
                <div>
                  <span>Payment failures (30d)</span>
                  <strong>{selected.payment_failures}</strong>
                </div>
              </div>
              <div className="copilot-placeholder">
                <p className="eyebrow">Retention Copilot</p>
                <p>
                  AI recommendations coming next — this panel will explain why
                  the customer is at risk and suggest retention actions.
                </p>
              </div>
            </div>
          ) : (
            <p className="muted">Select a customer to inspect risk drivers.</p>
          )}
        </section>
      </main>
    </div>
  )
}

export default App
