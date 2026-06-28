import { useEffect, useState } from "react";
import { ArrowLeft, Cloud, Database, Download, FileUp, Plus, Search, Trash2, Edit2 } from "lucide-react";
import { Link } from "react-router";
import { SettingRow } from "./ApiConfig";
import { get_capabilities } from "../../contracts/capability_map";
import { get_termbase, type TermbaseDTO } from "../../contracts/backend_bridge";

export function TermbaseManagement() {
  const capabilities = get_capabilities();
  const [termbase, setTermbase] = useState<TermbaseDTO>({});
  const [status, setStatus] = useState("Loading local termbase...");

  useEffect(() => {
    get_termbase()
      .then((payload) => {
        setTermbase(payload);
        const count = Object.values(payload).reduce((total, layer) => total + Object.keys(layer).length, 0);
        setStatus(count ? "" : "No local termbase entries.");
      })
      .catch((error: any) => setStatus(error?.message || "Backend contract bridge unavailable."));
  }, []);
  const terms = Object.entries(termbase).flatMap(([layer, rows]) =>
    Object.entries(rows).map(([source, target], index) => ({
      id: `${layer}-${index}-${source}`,
      source,
      target,
      domain: layer,
    })),
  );

  return (
    <main className="flex min-w-0 flex-1 flex-col bg-white/70 h-full">
      <div className="flex items-center gap-3 border-b bg-card/80 px-4 py-4 md:px-8 backdrop-blur">
        <Link to="/settings" className="grid size-10 place-items-center rounded-2xl border bg-card hover:bg-muted transition">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h2 className="text-xl font-bold">Termbase Management</h2>
          <p className="text-sm text-muted-foreground hidden sm:block">Manage local and cloud glossaries</p>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4 md:p-8">
        <div className="mx-auto max-w-5xl space-y-8 pb-8">
          
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-3xl border bg-card p-5 shadow-sm">
              <h3 className="font-bold mb-1">Local Termbase</h3>
              <p className="text-sm text-muted-foreground mb-4">Store terminology securely on this device.</p>
              <SettingRow icon={Database} title="Enable local termbase" desc={capabilities.learning_mode.reason || "Active"} on />
            </div>
            <div className="rounded-3xl border bg-card p-5 shadow-sm">
              <h3 className="font-bold mb-1">Cloud Termbase</h3>
              <p className="text-sm text-muted-foreground mb-4">Sync glossaries across devices.</p>
              <SettingRow icon={Cloud} title="Cloud termbase placeholder" desc={capabilities.cloud_termbase.reason} on={false} />
            </div>
          </div>

          <div className="rounded-3xl border bg-card p-5 md:p-6 shadow-sm flex flex-col">
            <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center mb-6">
              <h3 className="font-bold text-lg">Terms List</h3>
              <div className="flex gap-2 w-full sm:w-auto">
                <button disabled title="Export uses the Windows backend save dialog." className="flex-1 sm:flex-none flex items-center justify-center gap-2 rounded-xl border px-4 py-2 text-sm font-semibold hover:bg-muted transition disabled:cursor-not-allowed disabled:opacity-50">
                  <Download size={16} /> Export
                </button>
                <button disabled className="flex-1 sm:flex-none flex items-center justify-center gap-2 rounded-xl border px-4 py-2 text-sm font-semibold hover:bg-muted transition disabled:cursor-not-allowed disabled:opacity-50">
                  <FileUp size={16} /> Import
                </button>
                <button disabled className="flex-1 sm:flex-none flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition shadow-md shadow-primary/20 disabled:cursor-not-allowed disabled:opacity-50">
                  <Plus size={16} /> Add
                </button>
              </div>
            </div>

            <div className="relative mb-6">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <input
                disabled
                title="Search is not exposed in the termbase contract."
                className="w-full rounded-2xl border bg-input-background py-2.5 pl-10 pr-4 text-sm outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/10 transition"
                placeholder="Backend-loaded local terms"
              />
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th className="pb-3 font-semibold w-[25%]">Source Term</th>
                    <th className="pb-3 font-semibold w-[25%]">Translated Term</th>
                    <th className="pb-3 font-semibold">Domain</th>
                    <th className="pb-3 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {terms.map((term) => (
                    <tr key={term.id} className="border-b last:border-0 hover:bg-muted/30 transition">
                          <td className="py-4 pr-4 font-medium">{term.source}</td>
                          <td className="py-4 pr-4 font-medium text-primary">{term.target}</td>
                      <td className="py-4 pr-4"><span className="bg-secondary text-primary px-2.5 py-1 rounded-lg text-xs font-medium">{term.domain}</span></td>
                      <td className="py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button disabled className="p-1.5 text-muted-foreground hover:text-primary transition rounded-lg hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"><Edit2 size={16} /></button>
                          <button disabled className="p-1.5 text-muted-foreground hover:text-red-600 transition rounded-lg hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"><Trash2 size={16} /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {status && <div className="py-6 text-sm text-muted-foreground">{status}</div>}
            </div>
            
          </div>
        </div>
      </div>
    </main>
  );
}
