import { useCallback, useEffect, useRef, useState } from "react";
import { api, getErrorMessage, type Expense } from "../api/client";

const CATEGORIES = ["Fuel", "Hotel", "Food", "Travel", "Medical", "Shopping", "Miscellaneous"];

type SortKey = keyof Pick<Expense, "expense_date" | "vendor_name" | "total_amount" | "category_name">;
type SortDir = "asc" | "desc";

function sortExpenses(list: Expense[], key: SortKey, dir: SortDir): Expense[] {
  return [...list].sort((a, b) => {
    const av = a[key] ?? "";
    const bv = b[key] ?? "";
    const cmp = String(av).localeCompare(String(bv), undefined, { numeric: true });
    return dir === "asc" ? cmp : -cmp;
  });
}

export default function Expenses() {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [vendor, setVendor] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("expense_date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [exporting, setExporting] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loadList = useCallback(async (cat: string) => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (cat) params.set("category", cat);
      if (vendor) params.set("vendor", vendor);
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      const { data } = await api.get<Expense[]>(`/expenses?${params}`, {
        signal: abortRef.current.signal,
      });
      setExpenses(data);
    } catch (err) {
      if ((err as { name?: string }).name !== "CanceledError") {
        setError(getErrorMessage(err, "Failed to load expenses"));
      }
    } finally {
      setLoading(false);
    }
  }, [vendor, dateFrom, dateTo]);

  useEffect(() => { loadList(category); }, [category, vendor, dateFrom, dateTo, loadList]);

  const handleSearch = async () => {
    if (!query.trim()) { loadList(category); return; }
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.post<Expense[]>("/expenses/search", { query, limit: 50 }, {
        signal: abortRef.current.signal,
      });
      setExpenses(data);
    } catch (err) {
      if ((err as { name?: string }).name !== "CanceledError") {
        setError(getErrorMessage(err, "Search failed"));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleClearSearch = () => {
    setQuery("");
    loadList(category);
  };

  const exportReport = async (format: string) => {
    setExporting(format);
    try {
      const { data } = await api.get("/reports/export", {
        params: {
          format,
          category: category || undefined,
          vendor: vendor || undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        },
        responseType: "blob",
      });
      const url = URL.createObjectURL(new Blob([data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `expenses.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(getErrorMessage(err, "Export failed"));
    } finally {
      setExporting(null);
    }
  };

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const sortedExpenses = sortExpenses(expenses, sortKey, sortDir);

  const SortTh = ({ label, col }: { label: string; col: SortKey }) => (
    <th
      onClick={() => toggleSort(col)}
      style={{ cursor: "pointer", userSelect: "none", whiteSpace: "nowrap" }}
      aria-sort={sortKey === col ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
    >
      {label}{" "}
      <span style={{ opacity: sortKey === col ? 1 : 0.3, fontSize: "0.75em" }}>
        {sortKey === col ? (sortDir === "asc" ? "▲" : "▼") : "▲"}
      </span>
    </th>
  );

  return (
    <div>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem", flexWrap: "wrap", gap: "0.75rem" }}>
        <h2 style={{ margin: 0 }}>Expenses</h2>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {(["csv", "xlsx", "pdf"] as const).map((fmt) => (
            <button
              key={fmt}
              className="btn btn-outline btn-sm"
              onClick={() => exportReport(fmt)}
              disabled={exporting !== null}
              aria-label={`Export as ${fmt.toUpperCase()}`}
            >
              {exporting === fmt ? "…" : fmt.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div className="search-bar" style={{ gap: "0.5rem", flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: "1 1 320px", minWidth: 240 }}>
          <input
            className="input"
            placeholder='Natural language search, e.g. "hotel expenses from March"'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            aria-label="Search expenses"
          />
          {query && (
            <button
              onClick={handleClearSearch}
              style={{ position: "absolute", right: "0.75rem", top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "var(--muted)", fontSize: "1rem" }}
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>
        <input
          className="input"
          placeholder="Vendor"
          value={vendor}
          onChange={(e) => setVendor(e.target.value)}
          style={{ maxWidth: 180, minWidth: 140 }}
          aria-label="Filter by vendor"
        />
        <input
          className="input"
          type="date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          style={{ maxWidth: 170, minWidth: 140 }}
          aria-label="Filter from date"
        />
        <input
          className="input"
          type="date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          style={{ maxWidth: 170, minWidth: 140 }}
          aria-label="Filter to date"
        />
        <select
          className="input"
          style={{ maxWidth: 160, marginBottom: 0 }}
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          aria-label="Filter by category"
        >
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <button className="btn" onClick={handleSearch} disabled={loading} aria-label="Run search">
          {loading ? "Searching…" : "Search"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="card" style={{ color: "var(--danger, #f87171)", marginBottom: "1rem" }} role="alert">
          {error}
        </div>
      )}

      {/* Summary row */}
      {expenses.length > 0 && (
        <p style={{ fontSize: "0.875rem", color: "var(--muted)", marginBottom: "0.75rem" }}>
          {expenses.length} expense{expenses.length !== 1 ? "s" : ""}
          {expenses.filter((e) => e.is_duplicate).length > 0 && (
            <span style={{ color: "var(--warning)", marginLeft: "0.5rem" }}>
              · {expenses.filter((e) => e.is_duplicate).length} duplicate{expenses.filter((e) => e.is_duplicate).length > 1 ? "s" : ""}
            </span>
          )}
        </p>
      )}

      {/* Table */}
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <SortTh label="Date" col="expense_date" />
              <SortTh label="Vendor" col="vendor_name" />
              <SortTh label="Category" col="category_name" />
              <SortTh label="Amount" col="total_amount" />
              <th>Flags</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} style={{ color: "var(--muted)", textAlign: "center" }}>
                  Loading…
                </td>
              </tr>
            ) : sortedExpenses.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ color: "var(--muted)", textAlign: "center" }}>
                  No expenses found
                </td>
              </tr>
            ) : (
              sortedExpenses.map((e) => (
                <tr key={e.id} style={e.is_duplicate ? { opacity: 0.75 } : undefined}>
                  <td>{e.expense_date ?? "—"}</td>
                  <td>{e.vendor_name ?? "—"}</td>
                  <td>{e.category_name ?? "—"}</td>
                  <td style={{ fontVariantNumeric: "tabular-nums" }}>
                    {e.currency}{" "}
                    {e.total_amount
                      ? parseFloat(e.total_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })
                      : "—"}
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    {e.is_duplicate && <span className="badge dup">Duplicate</span>}
                    {e.classification_confidence != null && (
                      <span
                        className="badge"
                        style={{ marginLeft: e.is_duplicate ? 4 : 0 }}
                        title="AI classification confidence"
                      >
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
