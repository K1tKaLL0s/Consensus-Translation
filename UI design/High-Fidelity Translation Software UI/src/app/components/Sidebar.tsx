import { Sparkles, Clock3, Plus, ChevronDown, Archive, Settings, Bot } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router";

export function BotAvatar() {
  return (
    <div className="grid size-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-indigo-200 to-indigo-500 text-white shadow-lg shadow-indigo-200">
      <Bot size={24} />
    </div>
  );
}

function ModeCard({ active = false, title, desc, icon: Icon, onClick }: any) {
  return (
    <button
      onClick={onClick}
      className={`mb-3 flex w-full items-center gap-3 rounded-2xl border p-3 text-left transition hover:-translate-y-0.5 ${
        active ? "border-primary bg-secondary text-primary shadow-sm" : "bg-card hover:bg-muted/40"
      }`}
    >
      <div
        className={`size-4 rounded-full border ${
          active ? "border-primary ring-4 ring-primary/15" : "border-muted-foreground/40"
        }`}
      />
      <Icon size={22} />
      <div>
        <div className="text-sm font-semibold">{title}</div>
        <div className="text-xs text-muted-foreground">{desc}</div>
      </div>
    </button>
  );
}

export function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

  const isSettings = location.pathname.startsWith("/settings");
  const isHistory = location.pathname.startsWith("/history");
  const isLearning = location.pathname === "/learning";
  const isStandard = location.pathname === "/";

  return (
    <aside className="hidden w-[300px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar p-6 lg:flex overflow-y-auto">
      <Link to="/" className="flex items-center gap-3">
        <div className="grid size-11 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/25">
          <Sparkles size={22} />
        </div>
        <div>
          <h1 className="text-xl font-bold leading-tight">Lingua Agent</h1>
          <p className="text-xs text-muted-foreground">AI translation workspace</p>
        </div>
      </Link>

      <div className="mt-8 flex items-center justify-between">
        <Link to="/history" className={`flex items-center gap-2 font-semibold hover:text-primary ${isHistory ? 'text-primary' : ''}`}>
          <Clock3 size={18} />
          History
        </Link>
        <Link
          to="/"
          className="flex items-center gap-1 rounded-xl border bg-card px-3 py-1.5 text-sm text-primary shadow-sm hover:bg-muted"
        >
          <Plus size={16} />
          New
        </Link>
      </div>

      <div className="mt-4 rounded-2xl border bg-card p-3 text-sm text-muted-foreground">
        Recent tasks load from the desktop history store.
      </div>
      <Link to="/history" className="mx-auto mt-3 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        Open history <ChevronDown size={15} />
      </Link>

      <div className="mt-5 border-t pt-5">
        <h3 className="mb-3 text-sm font-bold">Translation mode</h3>
        <ModeCard
          active={isStandard}
          onClick={() => navigate("/")}
          title="Standard translation"
          desc="Fast, accurate daily use"
          icon={Sparkles}
        />
        <ModeCard
          active={isLearning}
          onClick={() => navigate("/learning")}
          title="Learning mode"
          desc="Train glossary and style"
          icon={Archive}
        />
      </div>

      <Link
        to="/settings"
        className={`mt-auto flex w-full items-center justify-between rounded-2xl border px-4 py-3 shadow-sm transition hover:bg-muted ${
          isSettings ? "bg-secondary text-primary border-primary/30" : "bg-card text-muted-foreground"
        }`}
      >
        <span className="flex items-center gap-2">
          <Settings size={18} />
          Settings
        </span>
        <ChevronDown className="-rotate-90" size={16} />
      </Link>
    </aside>
  );
}
