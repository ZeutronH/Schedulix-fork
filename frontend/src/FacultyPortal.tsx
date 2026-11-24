import { useState, useEffect } from "react";
import {
  Briefcase,
  Calendar,
  Clock,
  User,
  MapPin,
  Download,
  Bell,
  LogOut,
  AlertCircle,
  BookOpen,
  Award,
  Layers,
  ShieldCheck,
  CheckCircle2,
  Table as TableIcon,
  Grid as GridIcon,
} from "lucide-react";
import facultyApi from "./faculty-api";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function FacultyPortal() {
  const [token, setToken] = useState<string | null>(localStorage.getItem("schedulix_faculty_token"));
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  // Portal data
  const [profile, setProfile] = useState<any>(null);
  const [timetable, setTimetable] = useState<any>(null);
  const [announcements, setAnnouncements] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [downloadSuccess, setDownloadSuccess] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [activeTab, setActiveTab] = useState<"timetable" | "profile" | "announcements">("timetable");
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");

  useEffect(() => {
    if (token) {
      loadFacultyData();
    }
  }, [token]);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError("");

    try {
      const res = await facultyApi.post("/auth/faculty-login", {
        identifier: identifier.trim(),
        password: password.trim(),
      });

      if (res.data.access_token) {
        localStorage.setItem("schedulix_faculty_token", res.data.access_token);
        setToken(res.data.access_token);
      }
    } catch (err: any) {
      setLoginError(err.response?.data?.detail || "Invalid faculty credentials. Please check your Faculty ID or Email.");
    } finally {
      setLoginLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("schedulix_faculty_token");
    setToken(null);
    setProfile(null);
    setTimetable(null);
    setAnnouncements([]);
  }

  async function loadFacultyData() {
    setLoading(true);
    setError("");
    try {
      const [profRes, ttRes, annRes] = await Promise.all([
        facultyApi.get("/faculty/profile"),
        facultyApi.get("/faculty/timetable"),
        facultyApi.get("/faculty/announcements"),
      ]);

      setProfile(profRes.data);
      setTimetable(ttRes.data);
      setAnnouncements(annRes.data || []);
    } catch (err: any) {
      if (err.response?.status === 401) {
        handleLogout();
      } else {
        setError(err.response?.data?.detail || "Failed to load faculty schedule data.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleDownloadPNG() {
    try {
      setDownloading(true);
      setDownloadSuccess("");
      const res = await facultyApi.get("/faculty/timetable/download", { responseType: "blob" });

      const dispHeader = res.headers["content-disposition"];
      let filename = `Faculty_Timetable_${profile?.faculty?.faculty_id || "Schedule"}.png`;
      if (dispHeader && dispHeader.includes("filename=")) {
        const match = dispHeader.match(/filename=["']?([^"';]+)["']?/);
        if (match && match[1]) filename = match[1];
      }

      const blobUrl = window.URL.createObjectURL(new Blob([res.data], { type: "image/png" }));
      const link = document.createElement("a");
      link.href = blobUrl;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);

      setDownloadSuccess(`Downloaded ${filename} successfully!`);
      setTimeout(() => setDownloadSuccess(""), 4000);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to download faculty timetable image.");
    } finally {
      setDownloading(false);
    }
  }

  // If not logged in, render Faculty Login Screen
  if (!token) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8 border border-slate-100">
          <div className="flex items-center gap-3 mb-6">
            <div className="bg-indigo-600 text-white p-3 rounded-xl shadow-lg shadow-indigo-500/30">
              <Briefcase size={28} />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">Schedulix Faculty Portal</h1>
              <p className="text-xs text-slate-500">Official University Timetable System</p>
            </div>
          </div>

          <div className="bg-indigo-50/70 border border-indigo-100 rounded-xl p-3 mb-6 text-xs text-indigo-900">
            <p className="font-semibold">Faculty Access Only</p>
            <p className="text-slate-600 mt-0.5">
              Log in with your Faculty ID (e.g. FAC001) or university email address.
            </p>
          </div>

          {loginError && (
            <div className="mb-4 bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-xs flex items-center gap-2">
              <AlertCircle size={14} className="shrink-0" />
              <span>{loginError}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Faculty ID or University Email
              </label>
              <input
                required
                type="text"
                placeholder="e.g. FAC001 or faculty@university.edu"
                className="w-full border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Password</label>
              <input
                required
                type="password"
                placeholder="••••••••"
                className="w-full border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <span className="text-[11px] text-slate-400 mt-1 block">
                Initial default password: <code className="bg-slate-100 px-1 py-0.5 rounded">schedulix2026</code>
              </span>
            </div>

            <button
              type="submit"
              disabled={loginLoading}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 rounded-xl shadow-md transition-all text-sm disabled:opacity-50"
            >
              {loginLoading ? "Authenticating..." : "Sign In to Faculty Portal"}
            </button>
          </form>

          {/* Quick links to Student & Admin portals */}
          <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <a
              href="/student.html"
              className="text-indigo-600 hover:text-indigo-800 font-medium transition-colors"
            >
              Student Portal →
            </a>
            <a
              href="/"
              className="text-slate-500 hover:text-slate-800 font-medium transition-colors"
            >
              Administrator Login
            </a>
          </div>
        </div>
      </div>
    );
  }

  if (loading && !profile) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="text-center space-y-3">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600 mx-auto" />
          <p className="text-sm font-semibold text-slate-600">Loading faculty assignment & timetable...</p>
        </div>
      </div>
    );
  }

  const faculty = profile?.faculty;
  const dept = profile?.department;
  const limits = profile?.workload_limits;
  const classes = timetable?.classes || [];
  const summary = timetable?.summary || {};

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Navbar */}
      <header className="bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-30 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-indigo-600 p-2 rounded-xl text-white font-bold text-sm shadow-md shadow-indigo-500/30">
              <Briefcase size={20} />
            </div>
            <div>
              <h1 className="font-bold text-base tracking-tight leading-tight">Schedulix Faculty Portal</h1>
              <p className="text-[11px] text-indigo-300">Consolidated Teaching Timetable</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-semibold text-white">{faculty?.full_name || "Faculty Member"}</p>
              <p className="text-[11px] text-slate-400">
                {faculty?.faculty_id} • {faculty?.designation || "Faculty"} {dept?.code ? `(${dept.code})` : ""}
              </p>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold border border-slate-700 transition-all"
            >
              <LogOut size={13} />
              <span>Log out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Navigation Tabs */}
        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab("timetable")}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-xs transition-all ${
                activeTab === "timetable"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-200/60"
              }`}
            >
              <Calendar size={14} />
              <span>Consolidated Timetable</span>
              {classes.length > 0 && (
                <span className="bg-indigo-500/40 text-white px-1.5 py-0.2 rounded-full text-[10px]">
                  {classes.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab("profile")}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-xs transition-all ${
                activeTab === "profile"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-200/60"
              }`}
            >
              <User size={14} />
              <span>Profile & Teaching Workload</span>
            </button>

            <button
              onClick={() => setActiveTab("announcements")}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-xs transition-all ${
                activeTab === "announcements"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-200/60"
              }`}
            >
              <Bell size={14} />
              <span>Announcements</span>
              {announcements.length > 0 && (
                <span className="bg-amber-500 text-white px-1.5 py-0.2 rounded-full text-[10px]">
                  {announcements.length}
                </span>
              )}
            </button>
          </div>

          {activeTab === "timetable" && (
            <div className="flex items-center gap-2">
              <div className="flex items-center bg-slate-200/70 p-1 rounded-lg">
                <button
                  onClick={() => setViewMode("grid")}
                  className={`p-1.5 rounded-md text-xs font-semibold flex items-center gap-1 ${
                    viewMode === "grid" ? "bg-white text-indigo-700 shadow-xs" : "text-slate-600 hover:text-slate-900"
                  }`}
                  title="Weekly Grid View"
                >
                  <GridIcon size={14} />
                  <span className="hidden sm:inline">Grid</span>
                </button>
                <button
                  onClick={() => setViewMode("table")}
                  className={`p-1.5 rounded-md text-xs font-semibold flex items-center gap-1 ${
                    viewMode === "table" ? "bg-white text-indigo-700 shadow-xs" : "text-slate-600 hover:text-slate-900"
                  }`}
                  title="Tabular View"
                >
                  <TableIcon size={14} />
                  <span className="hidden sm:inline">Table</span>
                </button>
              </div>

              <button
                onClick={handleDownloadPNG}
                disabled={downloading || classes.length === 0}
                className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3.5 py-2 rounded-xl text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
              >
                <Download size={14} />
                <span>{downloading ? "Generating..." : "Download PNG"}</span>
              </button>
            </div>
          )}
        </div>

        {downloadSuccess && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-3 rounded-xl text-xs flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
            <span>{downloadSuccess}</span>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-xs flex items-center gap-2">
            <AlertCircle size={16} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* TAB 1: CONSOLIDATED TIMETABLE */}
        {activeTab === "timetable" && (
          <div className="space-y-6">
            {/* Faculty Academic Banner */}
            <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-6 rounded-2xl shadow-sm border border-slate-800">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-indigo-300 text-xs font-semibold uppercase tracking-wider">
                    <span>Department of {dept?.name || "Academic Department"}</span>
                    <span>•</span>
                    <span>{faculty?.designation || "Faculty Member"}</span>
                  </div>
                  <h2 className="text-2xl font-bold tracking-tight text-white">
                    {faculty?.full_name} — Consolidated Weekly Schedule
                  </h2>
                  <p className="text-xs text-slate-400">
                    Faculty ID: <span className="text-white font-mono">{faculty?.faculty_id}</span> • Combining all teaching assignments across sections & programmes
                  </p>
                </div>

                <div className="flex items-center gap-4 bg-white/10 px-4 py-3 rounded-xl backdrop-blur-sm text-xs">
                  <div>
                    <p className="text-slate-400">Scheduled Classes</p>
                    <p className="text-xl font-bold text-white">{classes.length}</p>
                  </div>
                  <div className="h-8 w-px bg-white/20" />
                  <div>
                    <p className="text-slate-400">Weekly Hours</p>
                    <p className="text-xl font-bold text-indigo-300">{summary.weekly_hours || 0} hrs</p>
                  </div>
                  <div className="h-8 w-px bg-white/20" />
                  <div>
                    <p className="text-slate-400">Sections Taught</p>
                    <p className="text-xl font-bold text-emerald-400">{summary.distinct_sections || 0}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Overlap / Conflict Alert */}
            {summary.conflicts && summary.conflicts.length > 0 && (
              <div className="bg-red-50 border border-red-300 text-red-900 p-4 rounded-xl text-xs space-y-2">
                <div className="flex items-center gap-2 font-bold text-sm text-red-800">
                  <AlertCircle size={18} />
                  <span>Warning: Schedule Overlap Detected ({summary.conflicts.length})</span>
                </div>
                <p>
                  The system detected overlapping classes in your schedule. Please notify the academic administrator.
                </p>
              </div>
            )}

            {classes.length === 0 ? (
              <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center space-y-3">
                <Calendar size={40} className="mx-auto text-slate-300" />
                <h3 className="font-bold text-base text-slate-800">No Published Classes Found</h3>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  No active published timetable classes are currently scheduled for your faculty ID. Check back once the semester timetable is generated and published by the administrator.
                </p>
              </div>
            ) : viewMode === "grid" ? (
              /* WEEKLY GRID VIEW (Monday to Saturday) */
              <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-x-auto p-4">
                <div className="min-w-[1080px] grid grid-cols-6 gap-3">
                  {[0, 1, 2, 3, 4, 5].map((dayIdx) => {
                    const dayClasses = classes.filter((c: any) => c.weekday === dayIdx);
                    dayClasses.sort((a: any, b: any) => a.start_minute - b.start_minute);

                    return (
                      <div key={dayIdx} className="space-y-3">
                        <div className="bg-slate-100/80 border border-slate-200/80 px-3 py-2 rounded-xl text-center">
                          <span className="font-bold text-xs text-slate-800">{DAYS[dayIdx]}</span>
                          <span className="text-[10px] text-slate-500 block">
                            {dayClasses.length} {dayClasses.length === 1 ? "class" : "classes"}
                          </span>
                        </div>

                        <div className="space-y-2 min-h-[350px]">
                          {dayClasses.length === 0 ? (
                            <div className="h-32 border-2 border-dashed border-slate-100 rounded-xl flex items-center justify-center text-[11px] text-slate-300 font-medium">
                              No Classes
                            </div>
                          ) : (
                            dayClasses.map((item: any) => {
                              const isLab = item.session_type === "LABORATORY";
                              return (
                                <div
                                  key={item.id}
                                  className={`p-3 rounded-xl border transition-all text-xs space-y-1.5 shadow-xs ${
                                    isLab
                                      ? "bg-purple-50/70 border-purple-200 hover:border-purple-300"
                                      : "bg-indigo-50/60 border-indigo-200 hover:border-indigo-300"
                                  }`}
                                >
                                  {/* Subject Code & Type */}
                                  <div className="flex items-center justify-between">
                                    <span className="font-mono font-bold text-slate-900 text-[11px]">
                                      {item.subject_code}
                                    </span>
                                    <span
                                      className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                                        isLab
                                          ? "bg-purple-200/80 text-purple-800"
                                          : "bg-indigo-200/80 text-indigo-800"
                                      }`}
                                    >
                                      {item.session_type}
                                    </span>
                                  </div>

                                  {/* Subject Name */}
                                  <div className="font-semibold text-slate-800 leading-tight">
                                    {item.subject}
                                  </div>

                                  {/* Section Identity Badge */}
                                  <div className="bg-white/80 border border-slate-200 px-2 py-1 rounded-lg">
                                    <div className="text-[10px] font-bold text-indigo-700">
                                      {item.section_code || `Section ${item.section?.name}`}
                                    </div>
                                    <div className="text-[9px] text-slate-500 truncate" title={item.section_display_name}>
                                      {item.section_display_name || item.programme}
                                    </div>
                                  </div>

                                  {/* Time & Room Info */}
                                  <div className="pt-1 border-t border-slate-200/60 flex items-center justify-between text-[10px] text-slate-600">
                                    <div className="flex items-center gap-1 font-medium">
                                      <Clock size={11} className="text-slate-400" />
                                      <span>{item.start} - {item.end}</span>
                                    </div>
                                    <div className="flex items-center gap-1 font-semibold text-slate-700">
                                      <MapPin size={11} className="text-slate-400" />
                                      <span>{item.room}</span>
                                    </div>
                                  </div>
                                </div>
                              );
                            })
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              /* TABULAR VIEW */
              <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
                <table className="table min-w-full text-xs">
                  <thead>
                    <tr>
                      <th>Day</th>
                      <th>Time</th>
                      <th>Subject</th>
                      <th>Type</th>
                      <th>Section Academic Identity</th>
                      <th>Programme & Semester</th>
                      <th>Classroom & Location</th>
                      <th>Duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {classes.map((c: any) => (
                      <tr key={c.id}>
                        <td className="font-semibold text-slate-800">{DAYS[c.weekday]}</td>
                        <td className="font-mono text-indigo-700 font-bold whitespace-nowrap">
                          {c.start} - {c.end}
                        </td>
                        <td>
                          <p className="font-bold text-slate-900">{c.subject}</p>
                          <p className="text-[11px] font-mono text-slate-500">{c.subject_code}</p>
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              c.session_type === "LABORATORY" ? "badge-purple" : "badge-blue"
                            }`}
                          >
                            {c.session_type}
                          </span>
                        </td>
                        <td>
                          <span className="font-bold text-indigo-700 block">
                            {c.section_code || `Section ${c.section?.name}`}
                          </span>
                          <span className="text-[11px] text-slate-500 block">
                            {c.section_display_name || c.section?.full_name || ""}
                          </span>
                        </td>
                        <td>
                          {c.programme} {c.semester ? `• Sem ${c.semester}` : ""}
                        </td>
                        <td>
                          <p className="font-semibold text-slate-800">{c.room}</p>
                          <p className="text-[10px] text-slate-400">
                            {c.building} {c.floor ? `• ${c.floor}` : ""}
                          </p>
                        </td>
                        <td className="text-slate-500">{c.duration} mins</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: PROFILE & WORKLOAD */}
        {activeTab === "profile" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Faculty Info Card */}
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
                <div className="flex items-center gap-3 border-b pb-4">
                  <div className="bg-indigo-50 p-3 rounded-xl text-indigo-600 font-bold">
                    <User size={24} />
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-slate-900">{faculty?.full_name}</h3>
                    <p className="text-xs text-indigo-600 font-semibold">{faculty?.designation || "Faculty"}</p>
                  </div>
                </div>

                <div className="space-y-2.5 text-xs">
                  <div>
                    <span className="text-slate-400 font-medium">Faculty ID</span>
                    <p className="font-mono font-bold text-slate-900">{faculty?.faculty_id}</p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Department</span>
                    <p className="font-semibold text-slate-900">{dept?.name || "Not assigned"}</p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">University Email</span>
                    <p className="text-slate-700">{faculty?.email}</p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Phone & WhatsApp</span>
                    <p className="text-slate-700">{faculty?.phone || "—"} / {faculty?.whatsapp_number || "—"}</p>
                  </div>
                </div>
              </div>

              {/* Qualifications & Specialisation Card */}
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
                <div className="flex items-center gap-3 border-b pb-4">
                  <div className="bg-purple-50 p-3 rounded-xl text-purple-600 font-bold">
                    <Award size={24} />
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-slate-900">Academic Qualifications</h3>
                    <p className="text-xs text-slate-500">Credentials & Domain Expertise</p>
                  </div>
                </div>

                <div className="space-y-3 text-xs">
                  <div>
                    <span className="text-slate-400 font-medium">Highest Qualification</span>
                    <p className="font-bold text-slate-900 text-sm mt-0.5">{faculty?.highest_qualification || "Ph.D."}</p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Area of Specialisation</span>
                    <p className="font-semibold text-indigo-700 mt-0.5">{faculty?.specialisation || "General"}</p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Cross-Department Teaching</span>
                    <p className="mt-0.5">
                      <span
                        className={`badge ${
                          limits?.cross_department_approved ? "badge-green" : "badge-gray"
                        }`}
                      >
                        {limits?.cross_department_approved ? "Approved Exception" : "Standard Department Only"}
                      </span>
                    </p>
                  </div>
                </div>
              </div>

              {/* Workload Limits & Capacity Card */}
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
                <div className="flex items-center gap-3 border-b pb-4">
                  <div className="bg-emerald-50 p-3 rounded-xl text-emerald-600 font-bold">
                    <ShieldCheck size={24} />
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-slate-900">Workload Protection</h3>
                    <p className="text-xs text-slate-500">Scheduler Hard Limits</p>
                  </div>
                </div>

                <div className="space-y-3 text-xs">
                  <div>
                    <div className="flex justify-between font-semibold mb-1">
                      <span>Weekly Classes Utilisation</span>
                      <span>{classes.length} / {limits?.max_classes_per_week || 20}</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-indigo-600 h-2 rounded-full transition-all"
                        style={{
                          width: `${Math.min(100, ((classes.length) / (limits?.max_classes_per_week || 20)) * 100)}%`
                        }}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-2 border-t text-[11px]">
                    <div>
                      <span className="text-slate-400">Max Classes / Day</span>
                      <p className="font-bold text-slate-900">{limits?.max_classes_per_day || 4} classes</p>
                    </div>
                    <div>
                      <span className="text-slate-400">Max Consecutive</span>
                      <p className="font-bold text-slate-900">{limits?.max_consecutive_hours || 3} hours</p>
                    </div>
                    <div>
                      <span className="text-slate-400">Min Rest Gap</span>
                      <p className="font-bold text-slate-900">{limits?.min_break_minutes || 0} mins</p>
                    </div>
                    <div>
                      <span className="text-slate-400">Remaining Capacity</span>
                      <p className="font-bold text-emerald-700">{summary?.remaining_capacity || 0} classes</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Daily Workload Breakdown (Mon - Sat) */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-3">
              <h3 className="font-bold text-sm text-slate-900">Weekly Daily Teaching Load (Mon - Sat)</h3>
              <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
                {[0, 1, 2, 3, 4, 5].map((dIdx) => {
                  const count = summary.classes_per_day?.[dIdx] || 0;
                  const maxDay = limits?.max_classes_per_day || 4;
                  return (
                    <div key={dIdx} className="border rounded-xl p-3 text-center space-y-1">
                      <span className="text-[11px] font-bold text-slate-600">{DAYS[dIdx]}</span>
                      <p className="text-xl font-bold text-indigo-700">{count}</p>
                      <span className="text-[10px] text-slate-400">Max {maxDay} classes</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Teaching Eligibility: Subjects & Semesters */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Subjects */}
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-3">
                <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2">
                  <BookOpen size={16} className="text-indigo-600" />
                  Eligible Teaching Subjects
                </h3>
                {(!profile?.eligible_subjects || profile.eligible_subjects.length === 0) ? (
                  <p className="text-xs text-slate-400 italic">No specific subject restrictions set (eligible for all department subjects).</p>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {profile.eligible_subjects.map((sub: any) => (
                      <div key={sub.id} className="border p-2 rounded-lg text-xs flex items-center justify-between">
                        <div>
                          <span className="font-bold text-indigo-700">{sub.code}</span>: {sub.name}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Semesters */}
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-3">
                <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2">
                  <Layers size={16} className="text-indigo-600" />
                  Eligible Academic Semesters
                </h3>
                {(!profile?.eligible_semesters || profile.eligible_semesters.length === 0) ? (
                  <p className="text-xs text-slate-400 italic">Eligible for all academic semesters (1 through 8).</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {profile.eligible_semesters.sort().map((semNum: number) => (
                      <span key={semNum} className="badge badge-purple px-3 py-1 text-xs">
                        Semester {semNum} (Year {Math.ceil(semNum / 2)})
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: ANNOUNCEMENTS */}
        {activeTab === "announcements" && (
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <div>
              <h3 className="font-bold text-base text-slate-900">Academic & Timetable Announcements</h3>
              <p className="text-xs text-slate-500">Official updates, published schedules, and assignments</p>
            </div>

            {announcements.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-6 text-center">No announcements recorded yet.</p>
            ) : (
              <div className="space-y-3">
                {announcements.map((a: any) => (
                  <div key={a.id} className="border rounded-xl p-4 flex items-start gap-3 bg-slate-50/50">
                    <div className="bg-indigo-100 text-indigo-700 p-2 rounded-lg shrink-0">
                      <Bell size={16} />
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center justify-between">
                        <h4 className="font-bold text-xs text-slate-900">{a.title}</h4>
                        <span className="text-[10px] text-slate-400">
                          {a.timestamp ? new Date(a.timestamp).toLocaleString() : ""}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600">
                        {a.details?.note || a.details?.comments || `Action: ${a.action} recorded in audit trail.`}
                      </p>
                      {a.details?.version_number && (
                        <span className="inline-block badge badge-blue text-[10px] mt-1">
                          Timetable Version {a.details.version_number}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
        Schedulix University Timetable Management System — Faculty Portal
      </footer>
    </div>
  );
}
