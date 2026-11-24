
import { useEffect, useState } from "react";
import axios from "axios";

import api from "./api";

import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import Scheduling from "./components/Scheduling";
import Timetable from "./components/Timetable";
import Management from "./components/Management";

function Login({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();

    setLoading(true);
    setError("");

    try {
      const response = await api.post("/auth/login", {
        username: username.trim(),
        password
      });

      if (!response.data?.access_token) {
        throw new Error("Backend did not return an access token.");
      }

      localStorage.setItem(
        "schedulix_token",
        response.data.access_token
      );

      onLogin();

    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        const status = err.response?.status;
        const detail = err.response?.data?.detail;

        if (!err.response) {
          setError(
            "Cannot connect to the backend. Check that the API is running."
          );
        } else if (status === 401) {
          setError(
            "Backend rejected the credentials. Check the admin account and password hash."
          );
        } else {
          setError(
            `Server error (${status}): ${detail || err.message}`
          );
        }
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unexpected login error.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-5 bg-navy">
      <form
        onSubmit={submit}
        className="bg-white rounded-2xl p-8 w-full max-w-md space-y-5"
      >
        <div className="text-center">
          <div className="inline-flex bg-indigo-600 text-white p-3 rounded-xl font-bold text-2xl">
            S
          </div>

          <h1 className="text-2xl font-bold mt-3">
            Schedulix
          </h1>

          <p className="text-sm text-slate-500">
            Administrator login
          </p>
        </div>

        <input
          className="field"
          placeholder="Username"
          value={username}
          onChange={e => setUsername(e.target.value)}
          autoComplete="username"
          required
        />

        <input
          className="field"
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />

        {error && (
          <p className="text-sm text-red-600">
            {error}
          </p>
        )}

        <button
          type="submit"
          className="primary w-full"
          disabled={loading}
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>

        <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
          <a
            href="/faculty.html"
            className="text-indigo-600 hover:text-indigo-800 font-semibold transition-colors"
          >
            Faculty Portal →
          </a>
          <a
            href="/student.html"
            className="text-indigo-600 hover:text-indigo-800 font-semibold transition-colors"
          >
            Student Portal →
          </a>
        </div>
      </form>
    </div>
  );
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(
    Boolean(localStorage.getItem("schedulix_token"))
  );

  const [page, setPage] = useState("Dashboard");
  const [admin, setAdmin] = useState<any>(null);

  useEffect(() => {
    if (!authenticated) return;

    api.get("/auth/me")
      .then(response => {
        setAdmin(response.data);
      })
      .catch(() => {
        localStorage.removeItem("schedulix_token");
        setAuthenticated(false);
        setAdmin(null);
      });
  }, [authenticated]);

  function logout() {
    localStorage.removeItem("schedulix_token");
    setAuthenticated(false);
    setAdmin(null);
  }

  if (!authenticated) {
    return (
      <Login
        onLogin={() => setAuthenticated(true)}
      />
    );
  }

  const pages: Record<string, React.ReactNode> = {
    Dashboard: <Dashboard />,
    "Timetable Generation": <Scheduling />,
    Timetables: <Timetable />,
    Scheduling: <Scheduling />,
    Departments: <Management type="Departments" />,
    Programmes: <Management type="Programmes" />,
    "Academic Years": <Management type="Academic Years" />,
    Semesters: <Management type="Semesters" />,
    Sections: <Management type="Sections" />,
    "Students & Enrolments": <Management type="Students & Enrolments" />,
    Students: <Management type="Students & Enrolments" />,
    Faculty: <Management type="Faculty" />,
    "Faculty Workload": <Management type="Faculty Workload" />,
    Subjects: <Management type="Subjects" />,
    Classrooms: <Management type="Classrooms" />,
    Campus: <Management type="Classrooms" />,
    "Faculty Assignments": <Management type="Faculty Assignments" />,
    Availability: <Management type="Availability" />,
    "Email Notifications": <Management type="Email Notifications" />,
    "Audit Logs": <Management type="Audit Logs" />
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar
        page={page}
        setPage={setPage}
        logout={logout}
      />

      <main className="flex-1 min-w-0">
        <header className="bg-white border-b px-8 py-4 flex justify-between">
          <div>
            <h2 className="font-semibold">{page}</h2>
            <p className="text-xs text-slate-500">
              University administration
            </p>
          </div>

          <div className="text-right">
            <p className="text-sm font-semibold">
              {admin?.username || "Administrator"}
            </p>
            <p className="text-xs text-slate-500">
              Administrator
            </p>
          </div>
        </header>

        <div className="p-6 md:p-8">
          {pages[page] || <Dashboard />}
        </div>
      </main>
    </div>
  );
}
