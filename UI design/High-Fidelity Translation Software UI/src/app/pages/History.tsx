import { useEffect, useState } from "react";
import { Clock3, Search, Filter, Trash2 } from "lucide-react";
import { Link } from "react-router";
import { list_history, type HistoryRecordDTO } from "../../contracts/backend_bridge";

export function History() {
  const [history, setHistory] = useState<HistoryRecordDTO[]>([]);
  const [status, setStatus] = useState("Loading desktop history...");

  useEffect(() => {
    list_history()
      .then((records) => {
        setHistory(records);
        setStatus(records.length ? "" : "No history records in the desktop store.");
      })
      .catch((error: any) => setStatus(error?.message || "Backend contract bridge unavailable."));
  }, []);

  return (
    <main className="flex min-w-0 flex-1 flex-col bg-white/70 h-full">
      <div className="flex items-center justify-between border-b bg-card/80 px-4 py-4 md:px-8 backdrop-blur">
        <div>
          <div className="flex items-center gap-2 text-lg font-bold">
            <Clock3 className="text-primary" size={20} /> History
          </div>
          <p className="text-sm text-muted-foreground hidden sm:block">View and manage past translation tasks</p>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4 md:p-8">
        <div className="mx-auto max-w-4xl space-y-6">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <input
                disabled
                title="History search is not exposed in the backend contract."
                className="w-full rounded-2xl border bg-card py-2.5 pl-10 pr-4 text-sm outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/10 transition"
                placeholder="Search history..."
              />
            </div>
            <div className="flex gap-2">
              <button disabled title="History filtering is not exposed in the backend contract." className="flex items-center gap-2 rounded-2xl border bg-card px-4 py-2.5 text-sm hover:bg-muted transition disabled:cursor-not-allowed disabled:opacity-50">
                <Filter size={16} /> Filter
              </button>
              <button disabled title="History deletion is available in the Windows workbench." className="flex items-center gap-2 rounded-2xl border border-red-200 text-red-600 bg-red-50/50 px-4 py-2.5 text-sm hover:bg-red-50 transition disabled:cursor-not-allowed disabled:opacity-50">
                <Trash2 size={16} /> Clear
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {history.map((item) => (
              <Link
                to={`/history/${item.id}`}
                key={item.id}
                className="flex items-center gap-4 rounded-2xl border bg-card p-4 transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="grid size-12 shrink-0 place-items-center rounded-xl text-blue-600 bg-blue-50">
                  <Clock3 size={20} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-base font-semibold">{item.run_id || item.id}</div>
                  <div className="mt-1 text-sm text-muted-foreground">
                    {item.source_language} → {item.target_language} · {item.mode || "-"} · {item.workflow_status || "-"}
                  </div>
                </div>
                <div className="text-sm text-muted-foreground whitespace-nowrap">
                  {item.rating === null ? "unrated" : `rating ${item.rating}`}
                </div>
              </Link>
            ))}
            {status && <div className="rounded-2xl border bg-card p-4 text-sm text-muted-foreground">{status}</div>}
          </div>
        </div>
      </div>
    </main>
  );
}
