import { BookOpen, FileText, History, LogOut, MessageSquare, Monitor, Moon, Settings, Sun, Upload, UserRound } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";

export function Layout() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><BookOpen size={22} /></span><span>DocuMind</span><small>AI document intelligence</small></div>
        <nav aria-label="Primary navigation">
          <NavLink to="/"><FileText size={18} /> Dashboard</NavLink>
          <NavLink to="/upload"><Upload size={18} /> Upload</NavLink>
          <NavLink to="/documents"><FileText size={18} /> Documents</NavLink>
          <NavLink to="/chat"><MessageSquare size={18} /> New chat</NavLink>
          <NavLink to="/history"><History size={18} /> History</NavLink>
          <NavLink to="/profile"><UserRound size={18} /> Profile</NavLink>
        </nav>
        <div className="sidebar-card">
          <Settings size={18} />
          <div><strong>Workspace</strong><span>Private document Q&A</span></div>
        </div>
        <button className="ghost row" onClick={() => { logout(); navigate("/login"); }}><LogOut size={18} /> Sign out</button>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <strong>{user?.full_name || user?.email}</strong>
            <span>Ask questions grounded in your uploaded documents.</span>
          </div>
          <button className="icon-button" aria-label={`Theme: ${theme}. Toggle theme`} title={`Theme: ${theme}`} onClick={toggleTheme}>{theme === "system" ? <Monitor size={18} /> : theme === "light" ? <Moon size={18} /> : <Sun size={18} />}</button>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
