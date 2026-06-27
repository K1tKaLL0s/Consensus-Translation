import { ArrowLeft, Monitor, Moon, Sun, Type } from "lucide-react";
import { Link } from "react-router";

export function AppearanceSettings() {
  return (
    <main className="flex min-w-0 flex-1 flex-col bg-white/70 h-full">
      <div className="flex items-center gap-3 border-b bg-card/80 px-4 py-4 md:px-8 backdrop-blur">
        <Link to="/settings" className="grid size-10 place-items-center rounded-2xl border bg-card hover:bg-muted transition">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h2 className="text-xl font-bold">Appearance</h2>
          <p className="text-sm text-muted-foreground hidden sm:block">Customize the look and feel of Lingua Agent</p>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4 md:p-8">
        <div className="mx-auto max-w-2xl space-y-8 pb-8">
          
          <div className="rounded-3xl border bg-card p-5 md:p-6 shadow-sm">
            <h3 className="font-bold mb-4">Theme</h3>
            <div className="grid gap-3 sm:grid-cols-3">
              {[
                { icon: Sun, label: "Light", active: true },
                { icon: Moon, label: "Dark", active: false },
                { icon: Monitor, label: "System", active: false },
              ].map((theme) => (
                <button disabled title="Appearance persistence is not exposed in the backend contract." key={theme.label} className={`flex flex-col items-center gap-3 rounded-2xl border p-5 transition disabled:cursor-not-allowed disabled:opacity-70 ${theme.active ? 'border-primary ring-2 ring-primary/10 bg-secondary/50' : ''}`}>
                  <div className={`grid size-12 place-items-center rounded-xl ${theme.active ? 'bg-primary text-primary-foreground' : 'bg-slate-100 text-slate-600'}`}>
                    <theme.icon size={24} />
                  </div>
                  <div className={`font-semibold text-sm ${theme.active ? 'text-primary' : ''}`}>{theme.label}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-3xl border bg-card p-5 md:p-6 shadow-sm">
            <h3 className="font-bold mb-4">Typography</h3>
            
            <div className="space-y-6">
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-semibold text-muted-foreground flex items-center gap-2"><Type size={16}/> Font Size</span>
                  <span className="text-sm font-medium">Medium</span>
                </div>
                <input disabled title="Appearance persistence is not exposed in the backend contract." type="range" min="1" max="3" defaultValue="2" className="w-full accent-primary disabled:cursor-not-allowed disabled:opacity-50" />
                <div className="flex justify-between text-xs text-muted-foreground mt-2">
                  <span>Small</span>
                  <span>Medium</span>
                  <span>Large</span>
                </div>
              </div>

              <div className="border-t pt-6">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-semibold text-muted-foreground">Interface Density</span>
                  <span className="text-sm font-medium">Comfortable</span>
                </div>
                <div className="grid grid-cols-2 gap-3 mt-3">
                  <button disabled title="Appearance persistence is not exposed in the backend contract." className="rounded-2xl border border-primary bg-secondary/50 p-4 text-center disabled:cursor-not-allowed disabled:opacity-70">
                    <div className="h-2 w-1/2 bg-primary/20 rounded-full mx-auto mb-2"></div>
                    <div className="h-2 w-3/4 bg-primary/20 rounded-full mx-auto"></div>
                    <div className="mt-3 text-sm font-semibold text-primary">Comfortable</div>
                  </button>
                  <button disabled title="Appearance persistence is not exposed in the backend contract." className="rounded-2xl border p-4 text-center transition disabled:cursor-not-allowed disabled:opacity-70">
                    <div className="h-2 w-1/2 bg-slate-200 rounded-full mx-auto mb-1.5"></div>
                    <div className="h-2 w-3/4 bg-slate-200 rounded-full mx-auto"></div>
                    <div className="mt-3 text-sm font-semibold text-muted-foreground">Compact</div>
                  </button>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </main>
  );
}
