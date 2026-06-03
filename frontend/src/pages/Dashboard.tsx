import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, getErrorMessage, type Summary } from "../api/client";
import { FileUpload } from "../components/FileUpload";

const COLORS = ["#3b9eff", "#34d399", "#fbbf24", "#a78bfa", "#f87171", "#fb923c"];

const fmt = (v: string | number) =>
  `₹${parseFloat(String(v)).toLocaleString("en-IN")}`;

function StatCard({ label, value, accent }: { label: string; value: React.ReactNode; accent?: boolean }) {
  return (
    <div className="card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={accent ? { color: "var(--warning)" } : undefined}>
        {value}
      </div>
    </div>
  );
}

const STATUS_ORDER = ["processing", "done", "failed"];
function statusBadgeClass(status: string) {
  if (status === "done") return "badge badge-success";
  if (status === "failed") return "badge badge-danger";
  return "badge";
}

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

  const trendData =
    summary?.monthly_trend.map((t) => ({
      label: `${t.year}-${String(t.month).padStart(2, "0")}`,
      total: t.total,
    })) ?? [];

  const recentBills = summary?.recent_bills
    ? [...summary.recent_bills].sort(
        (a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status)
      )
    : [];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h2>Dashboard</h2>
        <button className="btn btn-outline btn-sm" onClick={load} disabled={loadingData} aria-label="Refresh">
          {loadingData ? "Refreshing…" : "↻ Refresh"}
        </button>
      </div>

      {error && (
        <div className="card" style={{ color: "var(--danger, #f87171)", marginBottom: "1.5rem" }} role="alert">
          {error}
        </div>
      )}

      <div className="card-grid">
        <StatCard
          label="Total expenses"
          value={summary ? fmt(summary.total_expenses) : "—"}
        />
        <StatCard
          label="Bills processed"
          value={summary?.expense_count ?? "—"}
        />
        <StatCard
          label="Duplicate alerts"
          value={summary?.duplicate_count ?? 0}
          accent={(summary?.duplicate_count ?? 0) > 0}
        />
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ marginBottom: "1rem" }}>Upload bills</h3>
        <FileUpload onUploaded={load} />
      </div>

      {(categoryData.length > 0 || trendData.length > 0) && (
        <div className="chart-row">
          {categoryData.length > 0 && (
            <div className="card">
              <h3 style={{ marginBottom: "1rem" }}>By category</h3>
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={categoryData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {categoryData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => fmt(v)} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          {trendData.length > 0 && (
            <div className="card">
              <h3 style={{ marginBottom: "1rem" }}>Monthly trend</h3>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={trendData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2d3f56" vertical={false} />
                  <XAxis dataKey="label" stroke="#8ba3bf" fontSize={11} tickLine={false} />
                  <YAxis stroke="#8ba3bf" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v: number) => fmt(v)} />
                  <Bar dataKey="total" name="Total" fill="#3b9eff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {recentBills.length > 0 && (
        <div className="card" style={{ marginTop: "1.5rem" }}>
          <h3 style={{ marginBottom: "1rem" }}>Recent uploads</h3>
          <table className="table">
            <thead>
              <tr>
                <th>File</th>
                <th>Status</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {recentBills.map((b) => (
                <tr key={b.id}>
                  <td style={{ maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {b.filename}
                  </td>
                  <td>
                    <span className={statusBadgeClass(b.status)}>{b.status}</span>
                  </td>
                  <td>{new Date(b.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loadingData && !error && summary?.expense_count === 0 && (
        <div className="card" style={{ marginTop: "1.5rem", textAlign: "center", color: "var(--muted)", padding: "2.5rem" }}>
          <p style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>🧾</p>
          <p>No expenses yet. Upload your first bill above to get started.</p>
        </div>
      )}
    </div>
  );
}
