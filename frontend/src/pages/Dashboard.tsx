import { useCallback, useEffect, useRef, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, getErrorMessage, type Summary } from "../api/client";
import { FileUpload } from "../components/FileUpload";

const COLORS = ["#2563eb", "#7c3aed", "#db2777", "#059669", "#d97706", "#dc2626"];
const POLL_INTERVAL = 3000;

const fmt = (v: string | number) =>
  `₹${parseFloat(String(v)).toLocaleString("en-IN")}`;

function StatCard({
  label, value, accent, icon,
}: {
  label: string;
  value: React.ReactNode;
  accent?: boolean;
  icon: string;
}) {
  return (
    <div className="ds-stat-card">
      <div className="ds-stat-top">
        <span className="ds-stat-label">{label}</span>
        <span className="ds-stat-icon" aria-hidden="true">{icon}</span>
      </div>
      <div className="ds-stat-value" style={accent ? { color: "#dc2626" } : undefined}>
        {value}
      </div>
    </div>
  );
}

const STATUS_ORDER = ["processing", "pending", "completed", "failed"];
const isActiveStatus = (status: string) => status === "pending" || status === "processing";

function statusBadge(status: string) {
  if (status === "completed") return { cls: "ds-badge-done", label: "Done" };
  if (status === "failed") return { cls: "ds-badge-failed", label: "Failed" };
  if (status === "pending") return { cls: "ds-badge-processing", label: "Queued" };
  return { cls: "ds-badge-processing", label: "Processing" };
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="ds-tooltip">
      {label && <div className="ds-tooltip-label">{label}</div>}
      <div className="ds-tooltip-value">{fmt(payload[0].value)}</div>
    </div>
  );
};

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingData, setLoadingData] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoadingData(true);
    setError(null);
    try {
      const { data } = await api.get<Summary>("/expenses/summary");
      setSummary(data);
      return data;
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load summary"));
      return null;
    } finally {
      if (!silent) setLoadingData(false);
    }
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, []);

  const startPolling = useCallback(() => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      const data = await load(true);
      if (data && !data.recent_bills?.some((b) => isActiveStatus(b.status))) stopPolling();
    }, POLL_INTERVAL);
  }, [load, stopPolling]);

  useEffect(() => {
    const hasProcessing = summary?.recent_bills?.some((b) => isActiveStatus(b.status));
    if (hasProcessing && !pollRef.current) startPolling();
    else if (!hasProcessing) stopPolling();
    return stopPolling;
  }, [summary, startPolling, stopPolling]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = useCallback(async (id: number) => {
    setDeletingId(id);
    setDeleteError(null);
    try {
      await api.delete(`/bills/${id}`);
      await load(true);
    } catch (err) {
      setDeleteError(getErrorMessage(err, "Failed to delete"));
    } finally {
      setDeletingId(null);
    }
  }, [load]);

  const categoryData = summary
    ? Object.entries(summary.by_category)
        .map(([name, value]) => ({ name, value: parseFloat(value) }))
        .sort((a, b) => b.value - a.value)
    : [];

  const trendData = summary?.monthly_trend.map((t) => ({
    label: `${t.year}-${String(t.month).padStart(2, "0")}`,
    total: t.total,
  })) ?? [];

  const recentBills = summary?.recent_bills
    ? [...summary.recent_bills].sort(
        (a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status)
      )
    : [];

  const isPolling = pollRef.current !== null;

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

        *, *::before, *::after { box-sizing: border-box; }

        .ds-root {
          font-family: 'Inter', system-ui, sans-serif;
          color: #0a0a0a;
          background: #f5f5f4;
          min-height: 100vh;
          padding: 2rem 2.5rem;
          animation: fadeIn 0.2s ease;
        }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

        .ds-topbar {
          display: flex; align-items: flex-start; justify-content: space-between;
          margin-bottom: 2.5rem; gap: 1rem; flex-wrap: wrap;
        }
        .ds-eyebrow {
          font-size: 0.68rem; font-weight: 700; letter-spacing: 0.12em;
          text-transform: uppercase; color: #2563eb; margin: 0 0 0.2rem;
        }
        .ds-title {
          font-size: 2rem; font-weight: 900; letter-spacing: -0.04em;
          color: #0a0a0a; margin: 0; line-height: 1;
        }
        .ds-topbar-actions { display: flex; align-items: center; gap: 0.5rem; margin-top: 0.4rem; }

        .ds-live-pill {
          display: flex; align-items: center; gap: 0.35rem;
          font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
          color: #059669; background: #f0fdf4;
          border: 1.5px solid #86efac; border-radius: 100px;
          padding: 0.22rem 0.65rem;
        }
        .ds-live-dot {
          width: 5px; height: 5px; border-radius: 50%; background: #059669;
          animation: pulse 1.4s ease-in-out infinite;
        }

        .ds-btn {
          display: inline-flex; align-items: center; gap: 0.4rem;
          font-family: 'Inter', sans-serif; font-size: 0.8rem; font-weight: 600;
          color: #0a0a0a; background: #fff; border: 1.5px solid #d4d4d4;
          border-radius: 8px; padding: 0.45rem 0.9rem;
          cursor: pointer; transition: border-color 0.1s, background 0.1s;
          letter-spacing: -0.01em;
        }
        .ds-btn:hover:not(:disabled) { background: #f5f5f5; border-color: #a3a3a3; }
        .ds-btn:disabled { opacity: 0.4; cursor: not-allowed; }

        .ds-error {
          background: #fef2f2; border: 1.5px solid #fca5a5;
          border-radius: 10px; padding: 0.75rem 1rem;
          color: #b91c1c; font-size: 0.83rem; font-weight: 500;
          margin-bottom: 1.5rem;
        }

        .ds-stats {
          display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem; margin-bottom: 1.5rem;
        }
        .ds-stat-card {
          background: #fff; border: 1.5px solid #e5e5e5;
          border-radius: 12px; padding: 1.25rem 1.25rem 1rem;
          transition: border-color 0.1s;
        }
        .ds-stat-card:hover { border-color: #2563eb; }
        .ds-stat-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; }
        .ds-stat-label { font-size: 0.68rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #a3a3a3; }
        .ds-stat-icon { font-size: 0.9rem; }
        .ds-stat-value { font-size: 1.75rem; font-weight: 900; letter-spacing: -0.04em; color: #0a0a0a; line-height: 1; }

        .ds-divider { border: none; border-top: 1.5px solid #e5e5e5; margin: 1.5rem 0; }

        .ds-section-label {
          font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em;
          text-transform: uppercase; color: #a3a3a3; margin: 0 0 0.875rem;
        }

        .ds-upload-card {
          background: #fff; border: 1.5px solid #e5e5e5;
          border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem;
        }

        .ds-charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
        .ds-chart-card {
          background: #fff; border: 1.5px solid #e5e5e5;
          border-radius: 12px; padding: 1.25rem;
        }

        .ds-tooltip {
          background: #0a0a0a; border-radius: 8px; padding: 0.45rem 0.75rem; font-size: 0.8rem;
        }
        .ds-tooltip-label { color: #737373; font-size: 0.7rem; margin-bottom: 2px; }
        .ds-tooltip-value { color: #fff; font-weight: 800; letter-spacing: -0.02em; }

        .ds-table-card {
          background: #fff; border: 1.5px solid #e5e5e5;
          border-radius: 12px; overflow: hidden;
        }
        .ds-table-head {
          padding: 1rem 1.25rem 0.75rem; border-bottom: 1.5px solid #f5f5f5;
          display: flex; align-items: center; justify-content: space-between;
        }
        .ds-table-title { font-size: 0.85rem; font-weight: 800; letter-spacing: -0.02em; color: #0a0a0a; margin: 0; }
        .ds-table-count { font-size: 0.7rem; font-weight: 600; color: #a3a3a3; }
        .ds-table { width: 100%; border-collapse: collapse; }
        .ds-table th {
          padding: 0.55rem 1.25rem; text-align: left;
          font-size: 0.65rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
          color: #a3a3a3; border-bottom: 1.5px solid #f5f5f5; background: #fafafa;
        }
        .ds-table td {
          padding: 0.75rem 1.25rem; font-size: 0.83rem;
          color: #404040; border-bottom: 1px solid #f5f5f5; vertical-align: middle;
        }
        .ds-table tr:last-child td { border-bottom: none; }
        .ds-table tbody tr:hover td { background: #fafafa; }

        .ds-badge {
          display: inline-flex; align-items: center;
          font-size: 0.65rem; font-weight: 800; letter-spacing: 0.06em;
          text-transform: uppercase; border-radius: 6px;
          padding: 0.18rem 0.55rem; border: 1.5px solid;
        }
        .ds-badge-done { background: #f0fdf4; color: #15803d; border-color: #86efac; }
        .ds-badge-failed { background: #fef2f2; color: #b91c1c; border-color: #fca5a5; }
        .ds-badge-processing { background: #eff6ff; color: #1d4ed8; border-color: #93c5fd; animation: pulse 1.4s ease-in-out infinite; }

        .ds-filename { font-weight: 600; color: #0a0a0a; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; }

        .ds-delete-btn {
          display: inline-flex; align-items: center; justify-content: center;
          width: 28px; height: 28px; border-radius: 6px; border: 1.5px solid transparent;
          background: transparent; color: #d4d4d4; cursor: pointer; transition: all 0.1s;
        }
        .ds-delete-btn:hover:not(:disabled) { background: #fef2f2; border-color: #fca5a5; color: #b91c1c; }
        .ds-delete-btn:disabled { opacity: 0.35; cursor: not-allowed; }

        .ds-empty { text-align: center; padding: 4rem 1.5rem; }
        .ds-empty-icon {
          width: 48px; height: 48px; border-radius: 12px;
          background: #f5f5f5; border: 1.5px solid #e5e5e5;
          display: flex; align-items: center; justify-content: center;
          margin: 0 auto 1rem; font-size: 1.25rem;
        }
        .ds-empty-title { font-size: 0.9rem; font-weight: 800; color: #0a0a0a; margin: 0 0 0.25rem; letter-spacing: -0.02em; }
        .ds-empty-sub { font-size: 0.8rem; color: #a3a3a3; margin: 0; }
      `}</style>

      <div className="ds-root">
        <div className="ds-topbar">
          <div>
            <p className="ds-eyebrow">Bill Analyser</p>
            <h1 className="ds-title">Dashboard</h1>
          </div>
          <div className="ds-topbar-actions">
            {isPolling && (
              <span className="ds-live-pill">
                <span className="ds-live-dot" />
                Live
              </span>
            )}
            <button className="ds-btn" onClick={() => load()} disabled={loadingData} aria-label="Refresh">
              <svg width="12" height="12" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" style={loadingData ? { animation: "spin 0.7s linear infinite" } : undefined}>
                <path d="M4 4a8 8 0 0112.8 3M16 16a8 8 0 01-12.8-3" />
                <polyline points="3,4 4,10 10,9" /><polyline points="17,16 16,10 10,11" />
              </svg>
              {loadingData ? "Loading…" : "Refresh"}
            </button>
          </div>
        </div>

        {error && <div className="ds-error" role="alert">{error}</div>}
        {deleteError && <div className="ds-error" role="alert">{deleteError}</div>}

        <div className="ds-stats">
          <StatCard label="Total expenses" icon="₹" value={summary ? fmt(summary.total_expenses) : "—"} />
          <StatCard label="Bills processed" icon="📄" value={summary?.expense_count ?? "—"} />
          <StatCard
            label="Duplicate alerts" icon="⚠"
            value={Number(summary?.duplicate_count ?? 0)}
            accent={Number(summary?.duplicate_count ?? 0) > 0}
          />
        </div>

        <hr className="ds-divider" />

        <div className="ds-upload-card">
          <p className="ds-section-label">Upload bills</p>
          <FileUpload onUploaded={() => load()} />
        </div>

        {(categoryData.length > 0 || trendData.length > 0) && (
          <>
            <p className="ds-section-label">Analytics</p>
            <div className="ds-charts">
              {categoryData.length > 0 && (
                <div className="ds-chart-card">
                  <p className="ds-section-label">By category</p>
                  <ResponsiveContainer width="100%" height={240}>
                    <PieChart>
                      <Pie
                        data={categoryData} dataKey="value" nameKey="name"
                        cx="50%" cy="50%" outerRadius={88} innerRadius={44} paddingAngle={2}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        labelLine={false}
                      >
                        {categoryData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                      <Legend wrapperStyle={{ fontSize: "0.68rem", color: "#a3a3a3", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em" }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
              {trendData.length > 0 && (
              <div className="ds-chart-card">
                <p className="ds-section-label">Monthly trend</p>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={trendData} margin={{ top: 4, right: 4, bottom: 0, left: 32 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                    <XAxis
                      dataKey="label"
                      stroke="#d4d4d4"
                      fontSize={10}
                      fontWeight={700}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      stroke="#d4d4d4"
                      fontSize={10}
                      fontWeight={700}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => v < 1000 ? `₹${v}` : `₹${(v/1000).toFixed(0)}k`}
                      width={40}
                      domain={[0, (dataMax: number) => Math.ceil(dataMax * 1.2 / 1000) * 1000]}
                      tickCount={5}
                      allowDecimals={false}
                    />
                    {/* <YAxis
                      stroke="#d4d4d4"
                      fontSize={10}
                      fontWeight={700}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                      width={36}
                      domain={[0, 'auto']}
                      tickCount={5}
                      allowDecimals={false}
                    /> */}
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
                    <Bar dataKey="total" name="Total" fill="#2563eb" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              )}
            </div>
          </>
        )}

        {recentBills.length > 0 && (
          <div className="ds-table-card">
            <div className="ds-table-head">
              <p className="ds-table-title">Recent uploads</p>
              <span className="ds-table-count">{recentBills.length} bill{recentBills.length !== 1 ? "s" : ""}</span>
            </div>
            <table className="ds-table">
              <thead>
                <tr><th>File</th><th>Status</th><th>Uploaded</th><th></th></tr>
              </thead>
              <tbody>
                {recentBills.map((b) => {
                  const badge = statusBadge(b.status);
                  const isDeleting = deletingId === b.id;
                  return (
                    <tr key={b.id} style={isDeleting ? { opacity: 0.4 } : undefined}>
                      <td><span className="ds-filename">{b.filename}</span></td>
                      <td>
                        <span className={`ds-badge ${badge.cls}`}>{badge.label}</span>
                        {b.status === "failed" && b.error_message && (
                          <div style={{ color: "#b91c1c", fontSize: "0.75rem", marginTop: "0.25rem" }}>{b.error_message}</div>
                        )}
                      </td>
                      <td style={{ color: "#a3a3a3", fontSize: "0.75rem", fontWeight: 600 }}>
                        {new Date(b.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Kolkata" })}
                      </td>
                      <td style={{ width: 40, textAlign: "right" }}>
                        <button
                          className="ds-delete-btn"
                          disabled={isDeleting || b.status === "processing"}
                          onClick={() => handleDelete(b.id)}
                          title={b.status === "processing" ? "Cannot delete while processing" : "Delete"}
                          aria-label={`Delete ${b.filename}`}
                        >
                          {isDeleting
                            ? <svg width="13" height="13" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" style={{ animation: "spin 0.7s linear infinite" }}><path d="M4 4a8 8 0 0112.8 3M16 16a8 8 0 01-12.8-3"/><polyline points="3,4 4,10 10,9"/><polyline points="17,16 16,10 10,11"/></svg>
                            : <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>
                          }
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {!loadingData && !error && summary?.expense_count === 0 && (
          <div className="ds-empty">
            <div className="ds-empty-icon">🧾</div>
            <p className="ds-empty-title">No expenses yet</p>
            <p className="ds-empty-sub">Upload your first bill above to get started.</p>
          </div>
        )}
      </div>
    </>
  );
}
