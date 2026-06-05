import { useCallback, useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, getErrorMessage, type Summary } from "../api/client";
import { FileUpload } from "../components/FileUpload";

const COLORS = ["#f59e0b", "#34d399", "#60a5fa", "#a78bfa", "#f472b6", "#fb923c"];

const fmt = (v: string | number) =>
  `₹${parseFloat(String(v)).toLocaleString("en-IN")}`;

function StatCard({
  label, value, accent, icon,
}: {
  label: string;
  value: React.ReactNode;
  accent?: boolean;
  icon: React.ReactNode;
}) {
  return (
    <div className="ds-stat-card">
      <div className="ds-stat-icon">{icon}</div>
      <div className="ds-stat-body">
        <div className="ds-stat-label">{label}</div>
        <div className="ds-stat-value" style={accent ? { color: "#fb923c" } : undefined}>
          {value}
        </div>
      </div>
    </div>
  );
}

const STATUS_ORDER = ["processing", "done", "failed"];

function statusBadge(status: string) {
  if (status === "done") return { bg: "rgba(52,211,153,0.12)", color: "#34d399", border: "rgba(52,211,153,0.2)", label: "Done" };
  if (status === "failed") return { bg: "rgba(248,113,113,0.12)", color: "#f87171", border: "rgba(248,113,113,0.2)", label: "Failed" };
  return { bg: "rgba(251,191,36,0.1)", color: "#fbbf24", border: "rgba(251,191,36,0.2)", label: "Processing" };
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#13131f", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, padding: "0.5rem 0.75rem", fontSize: "0.8rem", color: "#e8e6e0" }}>
      {label && <div style={{ color: "rgba(232,230,224,0.5)", marginBottom: 2 }}>{label}</div>}
      <div style={{ color: "#f59e0b", fontWeight: 600 }}>{fmt(payload[0].value)}</div>
    </div>
  );
};

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingData, setLoadingData] = useState(true);

  const load = useCallback(async () => {
    setLoadingData(true);
    setError(null);
    try {
      const { data } = await api.get<Summary>("/expenses/summary");
      setSummary(data);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load summary"));
    } finally {
      setLoadingData(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

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

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

        .ds-root { font-family: 'DM Sans', sans-serif; color: #e8e6e0; animation: fadeUp 0.4s ease both; }
        @keyframes fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }

        .ds-topbar {
          display: flex; align-items: center; justify-content: space-between;
          margin-bottom: 2rem; flex-wrap: wrap; gap: 0.75rem;
        }
        .ds-title {
          font-family: 'Syne', sans-serif; font-size: 1.6rem; font-weight: 700;
          color: #f0ede6; letter-spacing: -0.03em; margin: 0;
        }
        .ds-refresh-btn {
          display: flex; align-items: center; gap: 0.4rem;
          background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
          border-radius: 8px; padding: 0.45rem 0.875rem;
          font-family: 'DM Sans', sans-serif; font-size: 0.8rem; color: rgba(232,230,224,0.6);
          cursor: pointer; transition: all 0.15s;
        }
        .ds-refresh-btn:hover:not(:disabled) { background: rgba(255,255,255,0.07); color: #e8e6e0; }
        .ds-refresh-btn:disabled { opacity: 0.4; cursor: not-allowed; }

        .ds-error {
          background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.18);
          border-radius: 10px; padding: 0.75rem 1rem; color: #fca5a5;
          font-size: 0.85rem; margin-bottom: 1.5rem;
        }

        .ds-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }

        .ds-stat-card {
          background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
          border-radius: 14px; padding: 1.25rem 1.25rem;
          display: flex; align-items: center; gap: 1rem;
          transition: border-color 0.15s, background 0.15s;
        }
        .ds-stat-card:hover { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.1); }
        .ds-stat-icon {
          width: 42px; height: 42px; border-radius: 10px;
          background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.15);
          display: flex; align-items: center; justify-content: center;
          color: #f59e0b; flex-shrink: 0; font-size: 1.1rem;
        }
        .ds-stat-label { font-size: 0.75rem; color: rgba(232,230,224,0.45); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem; }
        .ds-stat-value { font-family: 'Syne', sans-serif; font-size: 1.35rem; font-weight: 700; color: #f0ede6; letter-spacing: -0.02em; line-height: 1; }

        .ds-upload-card {
          background: rgba(245,158,11,0.04); border: 1px dashed rgba(245,158,11,0.2);
          border-radius: 14px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem;
          transition: border-color 0.15s, background 0.15s;
        }
        .ds-upload-card:hover { border-color: rgba(245,158,11,0.35); background: rgba(245,158,11,0.06); }
        .ds-upload-title { font-family: 'Syne', sans-serif; font-size: 0.9rem; font-weight: 600; color: #f0ede6; margin: 0 0 0.875rem; }

        .ds-charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
        .ds-chart-card {
          background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
          border-radius: 14px; padding: 1.25rem;
        }
        .ds-chart-title { font-family: 'Syne', sans-serif; font-size: 0.9rem; font-weight: 600; color: #f0ede6; margin: 0 0 1rem; }

        .ds-table-card {
          background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
          border-radius: 14px; overflow: hidden;
        }
        .ds-table-head { padding: 1rem 1.25rem 0.75rem; border-bottom: 1px solid rgba(255,255,255,0.06); }
        .ds-table-title { font-family: 'Syne', sans-serif; font-size: 0.9rem; font-weight: 600; color: #f0ede6; margin: 0; }
        .ds-table { width: 100%; border-collapse: collapse; }
        .ds-table th {
          padding: 0.6rem 1.25rem; text-align: left;
          font-size: 0.72rem; font-weight: 500; letter-spacing: 0.06em; text-transform: uppercase;
          color: rgba(232,230,224,0.35); border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .ds-table td { padding: 0.7rem 1.25rem; font-size: 0.85rem; color: rgba(232,230,224,0.75); border-bottom: 1px solid rgba(255,255,255,0.03); }
        .ds-table tr:last-child td { border-bottom: none; }
        .ds-table tr:hover td { background: rgba(255,255,255,0.02); }

        .ds-badge {
          display: inline-flex; align-items: center; padding: 0.2rem 0.55rem;
          border-radius: 5px; font-size: 0.72rem; font-weight: 500; border: 1px solid;
        }

        .ds-empty {
          text-align: center; padding: 3rem 1.5rem;
          color: rgba(232,230,224,0.3); font-size: 0.875rem;
        }
        .ds-empty-icon { font-size: 2rem; margin-bottom: 0.5rem; }
      `}</style>

      <div className="ds-root">
        <div className="ds-topbar">
          <h1 className="ds-title">Dashboard</h1>
          <button className="ds-refresh-btn" onClick={load} disabled={loadingData} aria-label="Refresh">
            <svg width="13" height="13" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={loadingData ? { animation: "spin 0.8s linear infinite" } : undefined}>
              <path d="M4 4a8 8 0 0112.8 3M16 16a8 8 0 01-12.8-3" /><polyline points="3,4 4,10 10,9" /><polyline points="17,16 16,10 10,11" />
            </svg>
            {loadingData ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        {error && <div className="ds-error" role="alert">{error}</div>}

        {/* Stats */}
        <div className="ds-stats">
          <StatCard
            label="Total expenses"
            value={summary ? fmt(summary.total_expenses) : "—"}
            icon={<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>}
          />
          <StatCard
            label="Bills processed"
            value={summary?.expense_count ?? "—"}
            icon={<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>}
          />
          <StatCard
            label="Duplicate alerts"
            value={summary?.duplicate_count ?? 0}
            accent={(summary?.duplicate_count ?? 0) > 0}
            icon={<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>}
          />
        </div>

        {/* Upload */}
        <div className="ds-upload-card">
          <p className="ds-upload-title">Upload bills</p>
          <FileUpload onUploaded={load} />
        </div>

        {/* Charts */}
        {(categoryData.length > 0 || trendData.length > 0) && (
          <div className="ds-charts">
            {categoryData.length > 0 && (
              <div className="ds-chart-card">
                <p className="ds-chart-title">By category</p>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={categoryData} dataKey="value" nameKey="name"
                      cx="50%" cy="50%" outerRadius={88} innerRadius={40}
                      paddingAngle={2}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      labelLine={false}
                    >
                      {categoryData.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: "0.75rem", color: "rgba(232,230,224,0.5)" }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}

            {trendData.length > 0 && (
              <div className="ds-chart-card">
                <p className="ds-chart-title">Monthly trend</p>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={trendData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey="label" stroke="rgba(232,230,224,0.25)" fontSize={10} tickLine={false} axisLine={false} />
                    <YAxis stroke="rgba(232,230,224,0.25)" fontSize={10} tickLine={false} axisLine={false} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                    <Bar dataKey="total" name="Total" fill="#f59e0b" radius={[5, 5, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}

        {/* Recent uploads table */}
        {recentBills.length > 0 && (
          <div className="ds-table-card">
            <div className="ds-table-head">
              <p className="ds-table-title">Recent uploads</p>
            </div>
            <table className="ds-table">
              <thead>
                <tr>
                  <th>File</th>
                  <th>Status</th>
                  <th>Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {recentBills.map((b) => {
                  const badge = statusBadge(b.status);
                  return (
                    <tr key={b.id}>
                      <td style={{ maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {b.filename}
                      </td>
                      <td>
                        <span className="ds-badge" style={{ background: badge.bg, color: badge.color, borderColor: badge.border }}>
                          {badge.label}
                        </span>
                      </td>
                      <td style={{ color: "rgba(232,230,224,0.4)", fontSize: "0.8rem" }}>
                        {new Date(b.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
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
            <p>No expenses yet. Upload your first bill above to get started.</p>
          </div>
        )}
      </div>
    </>
  );
}
