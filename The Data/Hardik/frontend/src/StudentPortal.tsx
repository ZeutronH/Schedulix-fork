import { useState, useEffect } from "react";
import {
  GraduationCap,
  Calendar,
  Clock,
  User,
  MapPin,
  Download,
  Bell,
  LogOut,
  AlertCircle,
  BookOpen,
  ShieldCheck,
} from "lucide-react";
import studentApi from "./student-api";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function formatTime(minute: number) {
  const h = Math.floor(minute / 60);
  const m = minute % 60;
  const period = h >= 12 ? "PM" : "AM";
  const displayH = h % 12 === 0 ? 12 : h % 12;
  return `${displayH}:${m.toString().padStart(2, "0")} ${period}`;
}

export default function StudentPortal() {
  const [token, setToken] = useState<string | null>(localStorage.getItem("schedulix_student_token"));
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
  const [activeTab, setActiveTab] = useState<"timetable" | "courses" | "announcements">("timetable");

  useEffect(() => {
    if (token) {
      loadStudentData();
    }
  }, [token]);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError("");

    try {
      const res = await studentApi.post("/auth/student-login", {
        identifier: identifier.trim(),
        password: password.trim(),
      });

      if (res.data.access_token) {
        localStorage.setItem("schedulix_student_token", res.data.access_token);
        setToken(res.data.access_token);
      }
    } catch (err: any) {
      setLoginError(err.response?.data?.detail || "Invalid student credentials. Please check your Student ID or Email.");
    } finally {
      setLoginLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("schedulix_student_token");
    setToken(null);
    setProfile(null);
    setTimetable(null);
    setAnnouncements([]);
  }

  async function loadStudentData() {
    setLoading(true);
    setError("");
    try {
      const [profRes, ttRes, annRes] = await Promise.all([
        studentApi.get("/student/profile"),
        studentApi.get("/student/timetable"),
        studentApi.get("/student/announcements"),
      ]);

      setProfile(profRes.data);
      setTimetable(ttRes.data);
      setAnnouncements(annRes.data || []);
    } catch (err: any) {
      if (err.response?.status === 401) {
        handleLogout();
      } else {
        setError(err.response?.data?.detail || "Failed to load academic assignment data.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleDownloadPNG() {
    try {
      setDownloadSuccess("");
      const res = await studentApi.get("/student/timetable/download", { responseType: "blob" });

      const dispHeader = res.headers["content-disposition"];
      let filename = `Timetable_${profile?.programme?.code || "Student"}_Section_${profile?.section?.name || "A"}.png`;
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
      alert(err.response?.data?.detail || "Failed to download timetable image.");
    }
  }

  // If not logged in, render Student Login Screen
  if (!token) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8 border border-slate-100">
          <div className="flex items-center gap-3 mb-6">
            <div className="bg-indigo-600 text-white p-3 rounded-xl shadow-lg shadow-indigo-500/30">
              <GraduationCap size={28} />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900">Schedulix Student Portal</h1>
              <p className="text-xs text-slate-500">Official University Timetable System</p>
            </div>
          </div>

          <div className="bg-indigo-50/70 border border-indigo-100 rounded-xl p-3 mb-6 text-xs text-indigo-900">
            <p className="font-semibold">Student Access Only</p>
            <p className="text-slate-600 mt-0.5">
              Log in with your Student ID (e.g. STU2026001) or university email address.
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
                Student ID or University Email
              </label>
              <input
                required
                type="text"
                placeholder="e.g. STU2026001 or student@example.edu"
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
              {loginLoading ? "Authenticating..." : "Sign In to Student Portal"}
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <a
              href="/faculty.html"
              className="text-indigo-600 hover:text-indigo-800 font-medium transition-colors"
            >
              Faculty Portal →
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
          <p className="text-sm font-semibold text-slate-600">Loading student assignment & timetable...</p>
        </div>
      </div>
    );
  }

  // Logged-in Student View
  const student = profile?.student;
  const dept = profile?.department;
  const prog = profile?.programme;
  const section = profile?.section;
  const semester = profile?.semester;
  const classes = timetable?.classes || [];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Navbar */}
      <header className="bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-30 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-indigo-600 p-2 rounded-xl text-white font-bold text-sm shadow-md shadow-indigo-500/30">
              <GraduationCap size={20} />
            </div>
            <div>
              <h1 className="font-bold text-base tracking-tight leading-tight">Schedulix Student Portal</h1>
              <p className="text-[11px] text-indigo-300">University Timetable Management</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-semibold text-white">{student?.full_name || "Student"}</p>
              <p className="text-[11px] text-slate-400">{student?.student_id} • Section {section?.name || "A"}</p>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold border border-slate-700 transition-all"
            >
              <LogOut size={13} />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm flex items-center gap-2">
            <AlertCircle size={16} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {downloadSuccess && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-3 rounded-xl text-xs flex items-center gap-2">
            <ShieldCheck size={16} className="shrink-0 text-emerald-600" />
            <span>{downloadSuccess}</span>
          </div>
        )}

        {/* Academic Hierarchy & Section Profile Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-2xl p-6 shadow-md border border-slate-800">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-indigo-300">
                <span className="bg-indigo-800/60 px-2 py-0.5 rounded border border-indigo-700/50">
                  {dept?.name || "Department of Computer Science"}
                </span>
                <span>•</span>
                <span>Year {student?.current_year || 1}</span>
                <span>•</span>
                <span>Semester {semester?.number || student?.current_semester || 1}</span>
              </div>
              <h2 className="text-2xl font-bold tracking-tight text-white">
                {prog?.name || "B.Tech Computer Science & Engineering"} — Section {section?.name || "A"}
              </h2>
              <p className="text-xs text-slate-400">
                Student: <span className="text-slate-200 font-medium">{student?.full_name}</span> ({student?.student_id}) • Admission Year: {student?.admission_year}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={handleDownloadPNG}
                disabled={classes.length === 0}
                className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2.5 rounded-xl text-xs font-bold shadow-md transition-all disabled:opacity-50"
              >
                <Download size={15} />
                <span>Download Official PNG Timetable</span>
              </button>
            </div>
          </div>

          <div className="mt-5 pt-4 border-t border-slate-800/80 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            <div>
              <p className="text-slate-400">Section Enrolment</p>
              <p className="text-base font-bold text-white mt-0.5">Section {section?.name || "A"}</p>
            </div>
            <div>
              <p className="text-slate-400">Weekly Classes</p>
              <p className="text-base font-bold text-emerald-400 mt-0.5">{classes.length} Sessions</p>
            </div>
            <div>
              <p className="text-slate-400">Timetable Status</p>
              <p className="text-base font-bold text-sky-400 mt-0.5">
                {timetable?.status === "PUBLISHED" ? `Official (v${timetable?.version?.version_number})` : "Unpublished"}
              </p>
            </div>
            <div>
              <p className="text-slate-400">Classroom Peers</p>
              <p className="text-base font-bold text-indigo-300 mt-0.5">{section?.student_count || 40} Students</p>
            </div>
          </div>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
          <button
            onClick={() => setActiveTab("timetable")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === "timetable"
                ? "bg-indigo-600 text-white shadow-sm"
                : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
            }`}
          >
            <Calendar size={14} />
            <span>Weekly Schedule Grid</span>
          </button>
          <button
            onClick={() => setActiveTab("courses")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === "courses"
                ? "bg-indigo-600 text-white shadow-sm"
                : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
            }`}
          >
            <BookOpen size={14} />
            <span>Faculty & Courses ({classes.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("announcements")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === "announcements"
                ? "bg-indigo-600 text-white shadow-sm"
                : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
            }`}
          >
            <Bell size={14} />
            <span>Announcements ({announcements.length})</span>
          </button>
        </div>

        {/* TAB 1: WEEKLY TIMETABLE GRID (MONDAY TO SATURDAY) */}
        {activeTab === "timetable" && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="font-bold text-base text-slate-900">Official Section Timetable</h3>
                <p className="text-xs text-slate-500">
                  Six-day academic schedule (Monday to Saturday) for Section {section?.name || "A"}.
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-indigo-50 text-indigo-700 font-semibold border border-indigo-200">
                  <span className="w-2 h-2 rounded-full bg-indigo-600" />
                  Lecture
                </span>
                <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-purple-50 text-purple-700 font-semibold border border-purple-200">
                  <span className="w-2 h-2 rounded-full bg-purple-600" />
                  Laboratory
                </span>
              </div>
            </div>

            {classes.length === 0 ? (
              <div className="p-12 text-center border-2 border-dashed border-slate-200 rounded-2xl">
                <Calendar size={36} className="mx-auto text-slate-300 mb-2" />
                <h4 className="font-bold text-slate-700 text-sm">No Published Timetable Yet</h4>
                <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                  The academic administration has not yet published an official timetable version for Section {section?.name || "A"}. Please check back soon or consult your department.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto pb-2">
                <div className="min-w-[1080px] grid grid-cols-6 gap-3">
                  {[0, 1, 2, 3, 4, 5].map((dayIdx) => {
                    const dayClasses = classes.filter((c: any) => c.weekday === dayIdx);
                    dayClasses.sort((a: any, b: any) => a.start_minute - b.start_minute);

                    return (
                      <div key={dayIdx} className="space-y-3">
                        <div className={`border rounded-xl p-2.5 text-center ${dayIdx === 5 ? "bg-amber-50/90 border-amber-200" : "bg-indigo-50/80 border-indigo-100"}`}>
                          <p className={`font-bold text-sm ${dayIdx === 5 ? "text-amber-950" : "text-indigo-950"}`}>
                            {DAYS[dayIdx]}
                          </p>
                          <p className={`text-[11px] font-medium ${dayIdx === 5 ? "text-amber-700" : "text-indigo-600"}`}>
                            {dayClasses.length} {dayClasses.length === 1 ? "Class" : "Classes"}
                          </p>
                        </div>

                        <div className="space-y-2.5">
                          {dayClasses.length === 0 ? (
                            <div className="p-4 border-2 border-dashed border-slate-200 rounded-xl text-center text-xs text-slate-400">
                              Free Day
                            </div>
                          ) : (
                            dayClasses.map((c: any) => {
                              const isLab = c.session_type === "LABORATORY";
                              return (
                                <div
                                  key={c.id}
                                  className={`p-3.5 rounded-xl border shadow-sm transition-all hover:shadow-md ${
                                    isLab
                                      ? "bg-purple-50/50 border-purple-200"
                                      : "bg-white border-slate-200"
                                  }`}
                                >
                                  <span className="inline-block text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 mb-1">
                                    {c.subject_code || "CS"}
                                  </span>
                                  <h4 className="font-bold text-xs text-slate-900 line-clamp-1" title={c.subject}>
                                    {c.subject}
                                  </h4>

                                  <div className="mt-2.5 space-y-1 text-[11px] text-slate-600">
                                    <div className="flex items-center gap-1.5 font-semibold text-slate-800">
                                      <Clock size={12} className="text-indigo-500 shrink-0" />
                                      <span>
                                        {formatTime(c.start_minute)} – {formatTime(c.end_minute)} ({c.duration}m)
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                      <User size={12} className="text-slate-400 shrink-0" />
                                      <span className="line-clamp-1">{c.faculty}</span>
                                    </div>
                                    <div className="flex items-center gap-1.5 text-blue-700 font-medium">
                                      <MapPin size={12} className="shrink-0" />
                                      <span className="line-clamp-1">
                                        {c.room} {c.building ? `(${c.building})` : ""}
                                      </span>
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
            )}
          </div>
        )}

        {/* TAB 2: FACULTY & COURSE DIRECTORY */}
        {activeTab === "courses" && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
            <div>
              <h3 className="font-bold text-base text-slate-900">Enrolled Courses & Faculty Assignments</h3>
              <p className="text-xs text-slate-500">
                All subject allocations, professors, and assigned classrooms for Section {section?.name || "A"}.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {classes.map((c: any) => (
                <div key={c.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-indigo-100 text-indigo-700">
                      {c.subject_code}
                    </span>
                    <span className="text-[11px] text-slate-500 font-semibold">{c.session_type}</span>
                  </div>
                  <h4 className="font-bold text-sm text-slate-900">{c.subject}</h4>
                  <div className="text-xs text-slate-600 space-y-1 pt-1 border-t border-slate-200/60">
                    <p className="flex items-center gap-1.5">
                      <User size={13} className="text-slate-400" />
                      <span>{c.faculty}</span>
                    </p>
                    <p className="flex items-center gap-1.5">
                      <MapPin size={13} className="text-slate-400" />
                      <span>{c.room} {c.building ? `(${c.building})` : ""}</span>
                    </p>
                    <p className="flex items-center gap-1.5">
                      <Clock size={13} className="text-slate-400" />
                      <span>{DAYS[c.weekday]}, {formatTime(c.start_minute)} – {formatTime(c.end_minute)}</span>
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 3: ANNOUNCEMENTS */}
        {activeTab === "announcements" && (
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
            <div>
              <h3 className="font-bold text-base text-slate-900">Timetable Announcements & Updates</h3>
              <p className="text-xs text-slate-500">Official notices regarding schedule releases and academic revisions.</p>
            </div>

            {announcements.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400">
                No new announcements at this time.
              </div>
            ) : (
              <div className="space-y-3">
                {announcements.map((a: any) => (
                  <div key={a.id} className="p-4 rounded-xl border border-slate-200 bg-indigo-50/40 space-y-1">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-sm text-slate-900">{a.title}</h4>
                      <span className="text-[11px] text-slate-500">{a.date}</span>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">{a.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 px-6 text-center text-xs text-slate-400">
        Schedulix University Timetable Management System • Relational DBMS & OS Scheduling Platform
      </footer>
    </div>
  );
}
