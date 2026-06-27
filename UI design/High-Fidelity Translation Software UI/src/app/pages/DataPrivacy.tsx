import { ArrowLeft, Trash2, Download, ShieldCheck, Database, History, AlertTriangle } from "lucide-react";
import { Link } from "react-router";
import { SettingRow } from "./ApiConfig";

export function DataPrivacy() {
  return (
    <main className="flex min-w-0 flex-1 flex-col bg-white/70 h-full">
      <div className="flex items-center gap-3 border-b bg-card/80 px-4 py-4 md:px-8 backdrop-blur">
        <Link to="/settings" className="grid size-10 place-items-center rounded-2xl border bg-card hover:bg-muted transition">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h2 className="text-xl font-bold">Data & Privacy</h2>
          <p className="text-sm text-muted-foreground hidden sm:block">Manage your local storage and data sharing preferences</p>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4 md:p-8">
        <div className="mx-auto max-w-2xl space-y-6 pb-8">
          
          <div className="rounded-3xl border border-indigo-100 bg-indigo-50/50 p-5 flex items-start gap-4">
            <ShieldCheck className="text-indigo-600 mt-0.5" size={24} />
            <div>
              <h3 className="font-semibold text-indigo-900">Privacy First Approach</h3>
              <p className="text-sm text-indigo-800 mt-1 leading-6">In <b>Local Mode</b>, all translations and terminology are processed on your device. No data is sent to external servers. In <b>AI Collaboration Mode</b>, data is sent to your configured API provider. Please refer to your API provider's privacy policy for data retention details.</p>
            </div>
          </div>

          <div className="rounded-3xl border bg-card p-5 md:p-6 shadow-sm space-y-2">
            <SettingRow icon={Database} title="Anonymous usage data" desc="Disabled; no telemetry contract is exposed." on={false} />
            <SettingRow icon={History} title="Save translation history" desc="Keep a record of all your past translations locally." on={true} />
          </div>

          <div className="rounded-3xl border bg-card p-5 md:p-6 shadow-sm">
            <h3 className="font-bold mb-4">Data Management</h3>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b pb-4">
                <div>
                  <div className="font-semibold text-sm">Export User Data</div>
                  <div className="text-sm text-muted-foreground mt-0.5">Download all history, settings, and termbases as a ZIP.</div>
                </div>
                <button disabled title="User data export is not exposed in the backend contract." className="rounded-xl border px-3 py-1.5 text-sm font-medium hover:bg-muted transition flex items-center gap-1.5 disabled:cursor-not-allowed disabled:opacity-50">
                  <Download size={16} /> Export
                </button>
              </div>

              <div className="flex items-center justify-between border-b pb-4">
                <div>
                  <div className="font-semibold text-sm">Clear Cache</div>
                  <div className="text-sm text-muted-foreground mt-0.5">Cache cleanup is not exposed in the backend contract.</div>
                </div>
                <button disabled title="Cache cleanup is not exposed in the backend contract." className="rounded-xl border px-3 py-1.5 text-sm font-medium hover:bg-muted transition disabled:cursor-not-allowed disabled:opacity-50">
                  Clear
                </button>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold text-sm text-red-600">Clear Translation History</div>
                  <div className="text-sm text-muted-foreground mt-0.5">Permanently delete all past translations from this device.</div>
                </div>
                <button disabled title="History deletion remains available in the Windows backend workbench." className="rounded-xl border border-red-200 bg-red-50 text-red-600 px-3 py-1.5 text-sm font-medium hover:bg-red-100 transition flex items-center gap-1.5 disabled:cursor-not-allowed disabled:opacity-50">
                  <Trash2 size={16} /> Delete All
                </button>
              </div>
            </div>
          </div>

        </div>
      </div>
    </main>
  );
}
