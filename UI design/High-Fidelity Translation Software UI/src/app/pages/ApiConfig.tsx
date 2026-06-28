import { useState } from "react";
import { ArrowLeft, KeyRound, ShieldAlert } from "lucide-react";
import { Link } from "react-router";
import { save_provider_settings, smoke_providers } from "../../contracts/backend_bridge";

export function SettingRow({ icon: Icon, title, desc, on = false }: any) {
  return (
    <div className="mt-4 flex items-center gap-4 rounded-2xl border bg-input-background p-4 cursor-default">
      <div className="grid size-10 place-items-center rounded-xl bg-secondary text-primary">
        <Icon size={19} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="font-semibold">{title}</div>
        <div className="text-sm text-muted-foreground">{desc}</div>
      </div>
      <div className={`h-7 w-12 rounded-full p-1 transition-colors ${on ? "bg-primary" : "bg-slate-300"}`}>
        <div className={`size-5 rounded-full bg-white shadow-sm transition-transform ${on ? "translate-x-5" : ""}`} />
      </div>
    </div>
  );
}

export function ApiConfig() {
  const [providerId, setProviderId] = useState("remote-main");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [status, setStatus] = useState("");

  async function saveConfiguration() {
    try {
      const result = await save_provider_settings({
        provider_id: providerId,
        base_url: baseUrl,
        model,
        api_key: apiKey,
        estimated_cost: 0,
        enabled: true,
      });
      setStatus(`Saved provider ${result.provider_id}`);
      setApiKey("");
    } catch (error: any) {
      setStatus(error?.message || "Backend contract bridge unavailable.");
    }
  }

  async function testConnection() {
    try {
      const result = await smoke_providers("hello");
      setStatus(result.lines.join("\n"));
    } catch (error: any) {
      setStatus(error?.message || "Backend contract bridge unavailable.");
    }
  }

  return (
    <main className="flex min-w-0 flex-1 flex-col bg-white/70 h-full">
      <div className="flex items-center gap-3 border-b bg-card/80 px-4 py-4 md:px-8 backdrop-blur">
        <Link to="/settings" className="grid size-10 place-items-center rounded-2xl border bg-card hover:bg-muted transition">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h2 className="text-xl font-bold">API Configuration</h2>
          <p className="text-sm text-muted-foreground hidden sm:block">OpenAI-compatible endpoint settings</p>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4 md:p-8">
        <div className="mx-auto max-w-2xl space-y-6 pb-8">
          
          <div className="rounded-3xl border bg-card p-5 md:p-6 shadow-sm">
            <SettingRow icon={KeyRound} title="Enable Custom API" desc="Use this API for cloud translation and learning tasks." on />
            
            <div className="mt-6 space-y-5">
              <label className="block">
                <span className="text-sm font-semibold">API Name</span>
                <input value={providerId} onChange={(event) => setProviderId(event.target.value)} className="mt-2 w-full rounded-2xl border bg-input-background p-3 font-normal outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/10 transition" />
              </label>

              <label className="block">
                <span className="text-sm font-semibold">Base URL</span>
                <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} className="mt-2 w-full rounded-2xl border bg-input-background p-3 font-normal outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/10 transition" placeholder="https://api.example.com/v1" />
              </label>

              <label className="block">
                <span className="text-sm font-semibold">API Key</span>
                <input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} className="mt-2 w-full rounded-2xl border bg-input-background p-3 font-normal outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/10 transition" />
                <div className="mt-2 flex items-center gap-1.5 text-xs text-amber-600 font-medium">
                  <ShieldAlert size={14} /> Keys are stored locally on your device.
                </div>
              </label>

              <div className="grid gap-5 sm:grid-cols-2">
                <label className="block">
                  <span className="text-sm font-semibold">Model Name</span>
                  <input value={model} onChange={(event) => setModel(event.target.value)} className="mt-2 w-full rounded-2xl border bg-input-background p-3 font-normal outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/10 transition" placeholder="provider model name" />
                </label>
                <label className="block">
                  <span className="text-sm font-semibold">Timeout</span>
                  <select disabled title="Timeout is controlled by the backend provider profile." className="mt-2 w-full rounded-2xl border bg-input-background p-3 font-normal outline-none transition disabled:cursor-not-allowed disabled:opacity-50">
                    <option>60 seconds</option>
                    <option>120 seconds</option>
                    <option>300 seconds</option>
                  </select>
                </label>
              </div>
            </div>

            <div className="mt-8 flex flex-col-reverse sm:flex-row gap-3">
              <button onClick={testConnection} className="rounded-2xl border px-5 py-3 text-sm font-semibold text-primary hover:bg-muted transition">Test Connection</button>
              <div className="flex-1" />
              <button onClick={saveConfiguration} className="rounded-2xl bg-primary px-8 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 hover:bg-primary/90 transition">Save Configuration</button>
            </div>
            {status && <pre className="mt-4 whitespace-pre-wrap rounded-2xl border bg-muted p-3 text-xs text-muted-foreground">{status}</pre>}
          </div>

          <div className="rounded-3xl border border-indigo-100 bg-indigo-50/50 p-5 text-sm text-indigo-900 leading-6">
            <b>Format compatibility:</b> Requests use standard <code className="bg-indigo-100 px-1.5 py-0.5 rounded text-indigo-800">/chat/completions</code> payloads. Save and test actions go through the backend provider contract.
          </div>

        </div>
      </div>
    </main>
  );
}
