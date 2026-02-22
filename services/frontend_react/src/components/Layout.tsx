import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function Layout({ children }: { children: React.ReactNode }) {
  const { isLoggedIn, logout } = useAuth();
  const navigate = useNavigate();
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = localStorage.getItem("theme") as "light" | "dark" | null;
    if (saved === "dark" || saved === "light") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

  const handleLogout = () => logout(window.location.origin);

  return (
    <>
      <header className="site-header">
        <div className="container">
          <button
            className="brand brand-button"
            type="button"
            onClick={() => navigate("/")}
            aria-label="Home"
          >
            <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M3 10.5L12 3l9 7.5" />
              <path d="M5 10v10h14V10" />
            </svg>
            <span className="brand-text">Simple SNS</span>
          </button>

          <nav className="nav">
            {/* Home */}
            <button
              className="button ghost nav-button icon-only"
              type="button"
              onClick={() => navigate("/")}
              aria-label="Home"
            >
              <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3 10.5L12 3l9 7.5" />
                <path d="M5 10v10h14V10" />
              </svg>
              <span className="sr-only">Home</span>
            </button>

            {/* Profile */}
            <button
              className="button ghost nav-button icon-only"
              type="button"
              onClick={() => navigate("/profile")}
              aria-label="Profile"
            >
              <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="8" r="4" />
                <path d="M4 20c1.8-3.5 5-5 8-5s6.2 1.5 8 5" />
              </svg>
              <span className="sr-only">Profile</span>
            </button>

            {/* Login / Logout */}
            {isLoggedIn ? (
              <button
                className="button ghost nav-button icon-only"
                type="button"
                onClick={handleLogout}
                aria-label="Logout"
              >
                <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M9 16l-4-4 4-4" />
                  <path d="M5 12h10" />
                  <path d="M13 5h6v14h-6" />
                </svg>
                <span className="sr-only">Logout</span>
              </button>
            ) : (
              <button
                className="button ghost nav-button icon-only"
                type="button"
                onClick={() => navigate("/login")}
                aria-label="Login"
              >
                <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M15 8l4 4-4 4" />
                  <path d="M19 12H9" />
                  <path d="M11 5H5v14h6" />
                </svg>
                <span className="sr-only">Login</span>
              </button>
            )}

            {/* Theme toggle */}
            <button
              className="button ghost theme-toggle icon-only"
              type="button"
              id="theme-toggle"
              onClick={toggleTheme}
              aria-pressed={theme === "dark"}
              aria-label="Toggle theme"
            >
              {/* Sun */}
              <svg
                className="icon icon-sun"
                viewBox="0 0 24 24"
                aria-hidden="true"
                style={{ display: theme === "dark" ? "block" : "none" }}
              >
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v3" />
                <path d="M12 19v3" />
                <path d="M2 12h3" />
                <path d="M19 12h3" />
                <path d="M4.5 4.5l2.1 2.1" />
                <path d="M17.4 17.4l2.1 2.1" />
                <path d="M4.5 19.5l2.1-2.1" />
                <path d="M17.4 6.6l2.1-2.1" />
              </svg>
              {/* Moon */}
              <svg
                className="icon icon-moon"
                viewBox="0 0 24 24"
                aria-hidden="true"
                style={{ display: theme === "light" ? "block" : "none" }}
              >
                <path d="M21 14.5A8.5 8.5 0 1 1 9.5 3a7 7 0 0 0 11.5 11.5z" />
              </svg>
              <span className="sr-only">Toggle theme</span>
            </button>
          </nav>
        </div>
      </header>

      <main className="container" style={{ paddingTop: "1rem" }}>
        {children}
      </main>
    </>
  );
}
