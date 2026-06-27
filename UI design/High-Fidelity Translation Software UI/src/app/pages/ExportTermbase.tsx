import { ArrowLeft, Download, FileJson } from "lucide-react";
import { Link } from "react-router";

export function ExportTermbase() {
  return (
    <main className="flex min-w-0 flex-1 flex-col bg-white/70 h-full">
      <div className="flex items-center gap-3 border-b bg-card/80 px-4 py-4 md:px-8 backdrop-blur">
        <Link to="/settings/termbase" className="grid size-10 place-items-center rounded-2xl border bg-card hover:bg-muted transition">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h2 className="text-xl font-bold">Export Termbase</h2>
          <p className="text-sm text-muted-foreground hidden sm:block">Download your terminology data</p>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4 md:p-8">
        <div className="mx-auto max-w-2xl space-y-6 pb-8">
          
          <div className="rounded-3xl border bg-card p-5 md:p-6 shadow-sm">
            <h3 className="font-bold mb-4">Export Scope</h3>
            <div className="space-y-3">
              {[
                { id: "all", label: "All Terms", desc: "Export all terms from the active local termbase." },
                { id: "current", label: "Current Project", desc: "Project-scoped export is not exposed in the current backend contract." },
                { id: "confirmed", label: "User Confirmed", desc: "Review-scoped export is not exposed in the current backend contract." },
              ].map((option, idx) => (
                <label key={option.id} className={`flex items-start gap-4 rounded-2xl border p-4 ${idx === 0 ? 'border-primary bg-secondary/50' : 'opacity-60'}`}>
                  <input disabled type="radio" name="scope" defaultChecked={idx === 0} className="mt-1" />
                  <div>
                    <div className={`font-semibold ${idx === 0 ? 'text-primary' : ''}`}>{option.label}</div>
                    <div className="text-sm text-muted-foreground mt-0.5">{option.desc}</div>
                  </div>
                </label>
              ))}
            </div>

            <h3 className="font-bold mb-4 mt-8">Export Format</h3>
            <div className="grid gap-3 sm:grid-cols-1">
              {[
                { icon: FileJson, label: "JSON", color: "text-yellow-600 bg-yellow-50" },
              ].map((fmt, idx) => (
                <label key={fmt.label} className={`flex flex-col items-center gap-3 rounded-2xl border p-5 text-center ${idx === 0 ? 'border-primary ring-2 ring-primary/10' : ''}`}>
                  <input disabled type="radio" name="format" defaultChecked={idx === 0} className="sr-only" />
                  <div className={`grid size-12 place-items-center rounded-xl ${fmt.color}`}>
                    <fmt.icon size={24} />
                  </div>
                  <div className="font-semibold text-sm">{fmt.label}</div>
                </label>
              ))}
            </div>

            <div className="mt-8 flex justify-end">
              <button disabled title="Export uses the Windows backend save dialog." className="w-full sm:w-auto rounded-2xl bg-primary px-8 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 hover:bg-primary/90 transition flex items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-50">
                <Download size={18} />
                Export Data
              </button>
            </div>
          </div>
          
        </div>
      </div>
    </main>
  );
}
