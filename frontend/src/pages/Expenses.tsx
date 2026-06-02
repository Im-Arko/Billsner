import { useEffect, useState } from "react";
import { api, type Expense } from "../api/client";

export default function Expenses() {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(false);

  const loadList = () => {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    api.get<Expense[]>(`/expenses?${params}`).then((r) => setExpenses(r.data));
  };

  useEffect(() => {
    loadList();
  }, [category]);

  const handleSearch = async () => {
    if (!query.trim()) {
      loadList();
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.post<Expense[]>("/expenses/search", {
        query,
        limit: 50,
      });
      setExpenses(data);
    } finally {
      setLoading(false);
    }
  };

  const exportReport = async (format: string) => {
    const { data } = await api.get(`/reports/export`, {
      params: { format },
      responseType: "blob",
    });
    const ext = format === "xlsx" ? "xlsx" : format;
    const url = URL.createObjectURL(new Blob([data]));
    const a = document.createElement("a");
    a.href = url;
    a.download = `expenses.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h2>Expenses</h2>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button className="btn btn-outline" onClick={() => exportReport("csv")}>
            CSV
          </button>
          <button className="btn btn-outline" onClick={() => exportReport("xlsx")}>
            Excel
          </button>
          <button className="btn btn-outline" onClick={() => exportReport("pdf")}>
            PDF
          </button>
        </div>
      </div>

      <div className="search-bar">
        <input
          className="input"
          placeholder='Natural language search, e.g. "hotel expenses from March"'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <select
          className="input"
          style={{ maxWidth: 160, marginBottom: 0 }}
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          <option value="">All categories</option>
          {["Fuel", "Hotel", "Food", "Travel", "Medical", "Shopping", "Miscellaneous"].map(
            (c) => (
              <option key={c} value={c}>
                {c}
              </option>
            )
          )}
        </select>
        <button className="btn" onClick={handleSearch} disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </button>
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Vendor</th>
              <th>Category</th>
              <th>Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {expenses.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ color: "var(--muted)" }}>
                  No expenses found
                </td>
              </tr>
            ) : (
              expenses.map((e) => (
                <tr key={e.id}>
                  <td>{e.expense_date ?? "—"}</td>
                  <td>{e.vendor_name ?? "—"}</td>
                  <td>{e.category_name ?? "—"}</td>
                  <td>
                    {e.currency} {e.total_amount ? parseFloat(e.total_amount).toLocaleString() : "—"}
                  </td>
                  <td>
                    {e.is_duplicate && <span className="badge dup">Duplicate</span>}
                    {e.classification_confidence != null && (
                      <span className="badge" style={{ marginLeft: 4 }}>
                        {Math.round(e.classification_confidence * 100)}%
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
