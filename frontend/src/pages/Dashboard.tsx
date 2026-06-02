import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type Summary } from "../api/client";
import { FileUpload } from "../components/FileUpload";

const COLORS = ["#3b9eff", "#34d399", "#fbbf24", "#a78bfa", "#f87171", "#fb923c"];

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);

  const load = () => {
    api.get<Summary>("/expenses/summary").then((r) => setSummary(r.data));
  };

  useEffect(() => {
    load();
  }, []);

  const categoryData = summary
    ? Object.entries(summary.by_category).map(([name, value]) => ({
        name,
        value: parseFloat(value),
      }))
    : [];

  const trendData =
    summary?.monthly_trend.map((t) => ({
      label: `${t.year}-${String(t.month).padStart(2, "0")}`,
      total: t.total,
    })) ?? [];

  return (
    <div>
      <h2 style={{ marginBottom: "1.5rem" }}>Dashboard</h2>

      <div className="card-grid">
        <div className="card">
          <div className="stat-label">Total expenses</div>
          <div className="stat-value">
            ₹{summary ? parseFloat(summary.total_expenses).toLocaleString() : "—"}
          </div>
        </div>
        <div className="card">
          <div className="stat-label">Bills processed</div>
          <div className="stat-value">{summary?.expense_count ?? "—"}</div>
        </div>
        <div className="card">
          <div className="stat-label">Duplicate alerts</div>
          <div className="stat-value" style={{ color: "var(--warning)" }}>
            {summary?.duplicate_count ?? 0}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ marginBottom: "1rem" }}>Upload bills</h3>
        <FileUpload onUploaded={load} />
      </div>

      <div className="chart-row">
        <div className="card">
          <h3 style={{ marginBottom: "1rem" }}>By category</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={categoryData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90}>
                {categoryData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v: number) => `₹${v.toLocaleString()}`} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <h3 style={{ marginBottom: "1rem" }}>Monthly trend</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3f56" />
              <XAxis dataKey="label" stroke="#8ba3bf" fontSize={11} />
              <YAxis stroke="#8ba3bf" fontSize={11} />
              <Tooltip formatter={(v: number) => `₹${v.toLocaleString()}`} />
              <Bar dataKey="total" fill="#3b9eff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {summary?.recent_bills && summary.recent_bills.length > 0 && (
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
              {summary.recent_bills.map((b) => (
                <tr key={b.id}>
                  <td>{b.filename}</td>
                  <td>
                    <span className="badge">{b.status}</span>
                  </td>
                  <td>{new Date(b.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
