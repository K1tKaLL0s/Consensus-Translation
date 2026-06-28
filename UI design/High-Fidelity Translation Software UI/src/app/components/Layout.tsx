import { Outlet, useLocation, useNavigate } from "react-router";
import { Sidebar } from "./Sidebar";
import { MobileNav } from "./MobileNav";

export function Layout() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background text-foreground flex justify-center items-center">
      {/* Desktop Container */}
      <div className="w-full h-screen lg:h-auto lg:min-h-[800px] lg:max-h-[900px] max-w-[1500px] flex overflow-hidden rounded-none lg:rounded-[28px] border-0 lg:border bg-card lg:shadow-2xl lg:shadow-slate-200/70 relative">
        {/* Desktop Sidebar (hidden on mobile) */}
        <Sidebar />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 bg-white/70 overflow-hidden relative pb-[90px] lg:pb-0">
          <Outlet />
        </div>

        {/* Mobile Navigation (hidden on desktop) */}
        <MobileNav />
      </div>
    </div>
  );
}
