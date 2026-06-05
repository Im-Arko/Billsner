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

const CATEGORY_COLORS: Record<string, string> = {
  Fuel: "#fb923c", Hotel: "#60a5fa", Food: "#34d399",
  Travel: "#a78bfa", Medical: "#f87171", Shopping: "#f472b6", Miscellaneous: "#94a3b8",
};

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

  const handleClearSearch = () => { setQuery(""); loadList(category); };

  const exportReport = async (format: string) => {
    setExporting(format);
    try {
      const { data } = await api.get("/reports/export", {
        params: { format, category: category || undefined, vendor: vendor || undefined, date_from: dateFrom || undefined, date_to: dateTo || undefined },
        responseType: "blob",
      });
      const url = URL.createObjectURL(new Blob([data]));
      const a = document.createElement("a");
      a.href = url; a.download = `expenses.${format}`; a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(getErrorMessage(err, "Export failed"));
    } finally {
      setExporting(null);
    }
  };

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("asc"); }
  };

  const sortedExpenses = sortExpenses(expenses, sortKey, sortDir);
  const dupCount = expenses.filter((e) => e.is_duplicate).length;

  const SortTh = ({ label, col }: { label: string; col: SortKey }) => (
    <th className="exp-th" onClick={() => toggleSort(col)} aria-sort={sortKey === col ? (sortDir === "asc" ? "ascending" : "descending") : "none"}>
      {label}
      <span className="exp-sort-arrow" style={{ opacity: sortKey === col ? 1 : 0.2 }}>
        {sortKey === col && sortDir === "desc" ? "↓" : "↑"}
      </span>
    </th>
  );

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700&family=DM+Sans:wght@300;400;500&display=swap');

        .exp-root { font-family: 'DM Sans', sans-serif; color: #e8e6e0; animation: fadeUp 0.4s ease both; }
        @keyframes fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }

        .exp-topbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 0.75rem; }
        .exp-title { font-family: 'Syne', sans-serif; font-size: 1.6rem; font-weight: 700; color: #f0ede6; letter-spacing: -0.03em; margin: 0; }

        .exp-export-group { display: flex; gap: 0.4rem; }
        .exp-export-btn {
          background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
          border-radius: 7px; padding: 0.4rem 0.75rem; font-size: 0.72rem; font-weight: 600;
          font-family: 'DM Sans', sans-serif; color: rgba(232,230,224,0.55); cursor: pointer;
          letter-spacing: 0.06em; text-transform: uppercase;
          transition: background 0.15s, color 0.15s, border-color 0.15s;
        }
        .exp-export-btn:hover:not(:disabled) { background: rgba(255,255,255,0.08); color: #e8e6e0; }
        .exp-export-btn:disabled { opacity: 0.4; cursor: not-allowed; }

        /* Filter bar */
        .exp-filters {
          background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
          border-radius: 14px; padding: 1rem 1.25rem;
          display: flex; flex-wrap: wrap; gap: 0.625rem; align-items: center;
          margin-bottom: 1rem;
        }

        .exp-search-wrap { position: relative; flex: 1 1 300px; min-width: 220px; }
        .exp-search-icon { position: absolute; left: 0.75rem; top: 50%; transform: translateY(-50%); color: rgba(232,230,224,0.25); pointer-events: none; display: flex; }
        .exp-clear-btn { position: absolute; right: 0.625rem; top: 50%; transform: translateY(-50%); background: none; border: none; cursor: pointer; color: rgba(232,230,224,0.3); font-size: 0.9rem; line-height: 1; padding: 0.2rem; transition: color 0.15s; }
        .exp-clear-btn:hover { color: rgba(232,230,224,0.6); }

        .exp-input {
          background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
          border-radius: 9px; padding: 0.6rem 0.875rem;
          font-family: 'DM Sans', sans-serif; font-size: 0.85rem; color: #e8e6e0;
          outline: none; width: 100%; box-sizing: border-box;
          transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
        }
        .exp-input::placeholder { color: rgba(232,230,224,0.2); }
        .exp-input:focus { border-color: rgba(245,158,11,0.4); background: rgba(245,158,11,0.04); box-shadow: 0 0 0 3px rgba(245,158,11,0.07); }
        .exp-search-field { padding-left: 2.25rem !important; }
        .exp-search-field-clear { padding-right: 2rem !important; }

        .exp-filter-input { flex: 0 1 150px; min-width: 120px; }
        .exp-filter-date { flex: 0 1 155px; min-width: 130px; }
        .exp-filter-select { flex: 0 1 160px; min-width: 130px; }

        .exp-search-btn {
          background: linear-gradient(135deg, #f59e0b, #d97706); border: none;
          border-radius: 9px; padding: 0.6rem 1.125rem;
          font-family: 'DM Sans', sans-serif; font-size: 0.85rem; font-weight: 500;
          color: #0a0a0f; cursor: pointer; white-space: nowrap;
          transition: opacity 0.15s, transform 0.15s;
          box-shadow: 0 2px 12px rgba(245,158,11,0.2);
        }
        .exp-search-btn:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
        .exp-search-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        .exp-meta { font-size: 0.8rem; color: rgba(232,230,224,0.35); margin-bottom: 0.75rem; }
        .exp-dup-warn { color: #fb923c; margin-left: 0.5rem; }

        .exp-error { background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.18); border-radius: 10px; padding: 0.75rem 1rem; color: #fca5a5; font-size: 0.85rem; margin-bottom: 1rem; }

        .exp-table-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; overflow: hidden; }
        .exp-table { width: 100%; border-collapse: collapse; }
        .exp-th {
          padding: 0.65rem 1rem; text-align: left;
          font-size: 0.72rem; font-weight: 500; letter-spacing: 0.06em; text-transform: uppercase;
          color: rgba(232,230,224,0.3); border-bottom: 1px solid rgba(255,255,255,0.05);
          cursor: pointer; user-select: none; white-space: nowrap;
          transition: color 0.15s;
        }
        .exp-th:hover { color: rgba(232,230,224,0.6); }
        .exp-sort-arrow { margin-left: 4px; font-size: 0.65em; }
        .exp-td { padding: 0.7rem 1rem; font-size: 0.85rem; color: rgba(232,230,224,0.7); border-bottom: 1px solid rgba(255,255,255,0.03); }
        .exp-tr:last-child .exp-td { border-bottom: none; }
        .exp-tr:hover .exp-td { background: rgba(255,255,255,0.02); color: rgba(232,230,224,0.9); }
        .exp-tr-dup .exp-td { opacity: 0.6; }

        .exp-amount { font-variant-numeric: tabular-nums; font-weight: 500; color: #f0ede6 !important; }

        .exp-cat-pill {
          display: inline-flex; align-items: center; gap: 0.35rem;
          padding: 0.15rem 0.55rem; border-radius: 999px;
          font-size: 0.72rem; font-weight: 500; border: 1px solid;
        }
        .exp-cat-dot { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }

        .exp-badge { display: inline-flex; align-items: center; padding: 0.15rem 0.5rem; border-radius: 5px; font-size: 0.7rem; font-weight: 600; border: 1px solid; margin-right: 4px; }
        .exp-conf { font-size: 0.7rem; color: rgba(232,230,224,0.35); }

        .exp-empty { text-align: center; padding: 2.5rem 1.5rem; color: rgba(232,230,224,0.3); font-size: 0.875rem; }
        .exp-loading { text-align: center; padding: 1.5rem; color: rgba(232,230,224,0.3); font-size: 0.875rem; }
      `}</style>

      <div className="exp-root">
        {/* Header */}
        <div className="exp-topbar">
          <h1 className="exp-title">Expenses</h1>
          <div className="exp-export-group">
            {(["csv", "xlsx", "pdf"] as const).map((fmt) => (
              <button
                key={fmt} className="exp-export-btn"
                onClick={() => exportReport(fmt)}
                disabled={exporting !== null}
                aria-label={`Export as ${fmt.toUpperCase()}`}
              >
                {exporting === fmt ? "…" : fmt}
              </button>
            ))}
          </div>
        </div>

        {/* Filters */}
        <div className="exp-filters">
          <div className="exp-search-wrap">
            <span className="exp-search-icon">
              <svg width="14" height="14" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round">
                <circle cx="9" cy="9" r="6"/><path d="M15 15l4 4"/>
              </svg>
            </span>
            <input
              className={`exp-input exp-search-field${query ? " exp-search-field-clear" : ""}`}
              placeholder='e.g. "hotel expenses from March"'
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              aria-label="Search expenses"
            />
            {query && (
              <button className="exp-clear-btn" onClick={handleClearSearch} aria-label="Clear search">✕</button>
            )}
          </div>

          <input className="exp-input exp-filter-input" placeholder="Vendor" value={vendor} onChange={(e) => setVendor(e.target.value)} aria-label="Filter by vendor" />
          <input className="exp-input exp-filter-date" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} aria-label="From date" />
          <input className="exp-input exp-filter-date" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} aria-label="To date" />
          <select className="exp-input exp-filter-select" value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Filter by category">
            <option value="">All categories</option>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <button className="exp-search-btn" onClick={handleSearch} disabled={loading}>
            {loading ? "Searching…" : "Search"}
          </button>
        </div>

        {error && <div className="exp-error" role="alert">{error}</div>}

        {expenses.length > 0 && (
          <p className="exp-meta">
            {expenses.length} expense{expenses.length !== 1 ? "s" : ""}
            {dupCount > 0 && (
              <span className="exp-dup-warn">
                · {dupCount} duplicate{dupCount > 1 ? "s" : ""}
              </span>
            )}
          </p>
        )}

        {/* Table */}
        <div className="exp-table-card">
          <table className="exp-table">
            <thead>
              <tr>
                <SortTh label="Date" col="expense_date" />
                <SortTh label="Vendor" col="vendor_name" />
                <SortTh label="Category" col="category_name" />
                <SortTh label="Amount" col="total_amount" />
                <th className="exp-th" style={{ cursor: "default" }}>Flags</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5} className="exp-loading">Loading…</td></tr>
              ) : sortedExpenses.length === 0 ? (
                <tr><td colSpan={5} className="exp-empty">No expenses found</td></tr>
              ) : (
                sortedExpenses.map((e) => {
                  const catColor = e.category_name ? (CATEGORY_COLORS[e.category_name] ?? "#94a3b8") : "#94a3b8";
                  return (
                    <tr key={e.id} className={`exp-tr${e.is_duplicate ? " exp-tr-dup" : ""}`}>
                      <td className="exp-td" style={{ color: "rgba(232,230,224,0.45)", fontSize: "0.8rem", whiteSpace: "nowrap" }}>
                        {e.expense_date ?? "—"}
                      </td>
                      <td className="exp-td" style={{ fontWeight: 500, color: "#e8e6e0" }}>
                        {e.vendor_name ?? "—"}
                      </td>
                      <td className="exp-td">
                        {e.category_name ? (
                          <span className="exp-cat-pill" style={{ background: `${catColor}12`, color: catColor, borderColor: `${catColor}25` }}>
                            <span className="exp-cat-dot" style={{ background: catColor }} />
                            {e.category_name}
                          </span>
                        ) : "—"}
                      </td>
                      <td className="exp-td exp-amount">
                        {e.currency} {e.total_amount
                          ? parseFloat(e.total_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })
                          : "—"}
                      </td>
                      <td className="exp-td" style={{ whiteSpace: "nowrap" }}>
                        {e.is_duplicate && (
                          <span className="exp-badge" style={{ background: "rgba(251,146,60,0.1)", color: "#fb923c", borderColor: "rgba(251,146,60,0.2)" }}>
                            Dup
                          </span>
                        )}
                        {e.classification_confidence != null && (
                          <span className="exp-conf" title="AI classification confidence">
                            {Math.round(e.classification_confidence * 100)}%
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
