import { BookOpen, FileText, History, LogOut, MessageSquare, Upload, UserRound } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><BookOpen size={26} /> <span>DocuMind</span></div>
        <nav>
          <NavLink to="/"><FileText size={18} /> Dashboard</NavLink>
          <NavLink to="/upload"><Upload size={18} /> Upload</NavLink>
          <NavLink to="/documents"><FileText size={18} /> Documents</NavLink>
          <NavLink to="/chat"><MessageSquare size={18} /> New chat</NavLink>
          <NavLink to="/history"><History size={18} /> History</NavLink>
          <NavLink to="/profile"><UserRound size={18} /> Profile</NavLink>
        </nav>
        <button className="ghost row" onClick={() => { logout(); navigate("/login"); }}><LogOut size={18} /> Sign out</button>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <strong>{user?.full_name || user?.email}</strong>
            <span>Ask questions grounded in your uploaded documents.</span>
          </div>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
