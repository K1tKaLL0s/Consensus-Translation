import { Sparkles, Clock3, Settings } from "lucide-react";
import { Link, useLocation } from "react-router";

export function MobileNav() {
  const location = useLocation();

  const isSettings = location.pathname.startsWith("/settings");
  const isHistory = location.pathname.startsWith("/history");
  const isTranslate = location.pathname === "/";

  return (
    <div className="lg:hidden fixed bottom-0 left-0 right-0 border-t bg-card/80 backdrop-blur px-4 py-3 pb-6 flex items-center justify-around z-50">
      <Link to="/" className={`flex flex-col items-center gap-1 ${isTranslate ? 'text-primary' : 'text-muted-foreground'}`}>
        <div className={`p-1.5 rounded-xl ${isTranslate ? 'bg-secondary' : ''}`}>
          <Sparkles size={22} />
        </div>
        <span className="text-[10px] font-medium">Translate</span>
      </Link>
      <Link to="/history" className={`flex flex-col items-center gap-1 ${isHistory ? 'text-primary' : 'text-muted-foreground'}`}>
        <div className={`p-1.5 rounded-xl ${isHistory ? 'bg-secondary' : ''}`}>
          <Clock3 size={22} />
        </div>
        <span className="text-[10px] font-medium">History</span>
      </Link>
      <Link to="/settings" className={`flex flex-col items-center gap-1 ${isSettings ? 'text-primary' : 'text-muted-foreground'}`}>
        <div className={`p-1.5 rounded-xl ${isSettings ? 'bg-secondary' : ''}`}>
          <Settings size={22} />
        </div>
        <span className="text-[10px] font-medium">Settings</span>
      </Link>
    </div>
  );
}
