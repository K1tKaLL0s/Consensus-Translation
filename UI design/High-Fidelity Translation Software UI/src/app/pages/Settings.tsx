import { Database, Download, Sparkles, ShieldCheck, PaintBucket, Info, ChevronRight, KeyRound } from "lucide-react";
import { Link } from "react-router";

function SettingLink({ icon: Icon, title, desc, to }: any) {
  return (
    <Link to={to} className="flex items-center gap-4 rounded-2xl border bg-card p-4 hover:shadow-md transition hover:-translate-y-0.5">
      <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-secondary text-primary">
        <Icon size={19} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="font-semibold">{title}</div>
        <div className="text-sm text-muted-foreground">{desc}</div>
      </div>
      <ChevronRight className="text-muted-foreground" size={20} />
    </Link>
  );
}

export function Settings() {
  return (
    <main className="flex min-w-0 flex-1 flex-col bg-white/70 h-full">
      <div className="border-b bg-card/80 px-4 py-4 md:px-8 md:py-5 backdrop-blur">
        <h2 className="text-xl font-bold">Settings</h2>
        <p className="text-sm text-muted-foreground hidden sm:block">Manage your translation engine, terminology, and preferences</p>
      </div>

      <div className="flex-1 overflow-auto p-4 md:p-8">
        <div className="mx-auto max-w-3xl space-y-8 pb-8">
          
          <section>
            <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-muted-foreground">General & Appearance</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <SettingLink icon={PaintBucket} title="Appearance" desc="Theme, density, and font size" to="/settings/appearance" />
              <SettingLink icon={ShieldCheck} title="Data & Privacy" desc="Manage local data and cache" to="/settings/privacy" />
            </div>
          </section>

          <section>
            <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-muted-foreground">Translation & Engine</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <SettingLink icon={Sparkles} title="Translation Engine" desc="Default behaviors and tone" to="/settings/api" />
              <SettingLink icon={KeyRound} title="API Configuration" desc="OpenAI-compatible endpoints" to="/settings/api" />
            </div>
          </section>

          <section>
            <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-muted-foreground">Terminology</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <SettingLink icon={Database} title="Termbase Management" desc="Local and cloud glossaries" to="/settings/termbase" />
              <SettingLink icon={Download} title="Export Termbase" desc="JSON export through the Windows backend" to="/settings/termbase/export" />
            </div>
          </section>

          <section>
            <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-muted-foreground">About</h3>
            <div className="flex items-center gap-4 rounded-2xl border bg-card p-4">
              <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-600">
                <Info size={19} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-semibold">Lingua Agent</div>
                <div className="text-sm text-muted-foreground">Version comes from the Windows package metadata.</div>
              </div>
              <button disabled title="Update checks are not exposed in the backend contract." className="text-sm font-semibold text-primary disabled:cursor-not-allowed disabled:opacity-50">Check for updates</button>
            </div>
          </section>

        </div>
      </div>
    </main>
  );
}
