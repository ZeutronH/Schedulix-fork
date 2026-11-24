import { useEffect, useState } from "react";
import {
  Download, RefreshCw, AlertCircle,
  Clock, MapPin, User,
  Filter, ShieldCheck,
  Edit2, X, Play
} from "lucide-react";
import api from "../api";
import type { TimetableEntry, TimetableVersion, Department, Programme, Section, Semester } from "../types";

const DAYS = [
  "Monday", "Tuesday", "Wednesday",
  "Thursday", "Friday", "Saturday", "Sunday"
];

export default function Timetable() {
  const [versions, setVersions] = useState<TimetableVersion[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [semesters, setSemesters] = useState<Semester[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [rooms, setRooms] = useState<any[]>([]);
  const [facultyList, setFacultyList] = useState<any[]>([]);

  // Selected filters
  const [selectedVersion, setSelectedVersion] = useState("");
  const [selectedDept, setSelectedDept] = useState("");
  const [selectedProg, setSelectedProg] = useState("");
  const [selectedSem, setSelectedSem] = useState("");
  const [selectedSection, setSelectedSection] = useState("");

  const [classes, setClasses] = useState<TimetableEntry[]>([]);
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
  const [workingDaysCount, setWorkingDaysCount] = useState<5 | 6>(6);
  const [loading, setLoading] = useState(false);
  const [generatingSection, setGeneratingSection] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Rescheduling Modal State
  const [rescheduleSession, setRescheduleSession] = useState<TimetableEntry | null>(null);
  const [rescheduleDay, setRescheduleDay] = useState(0);
  const [rescheduleStart, setRescheduleStart] = useState(480);
  const [rescheduleEnd, setRescheduleEnd] = useState(540);
  const [rescheduleRoom, setRescheduleRoom] = useState("");
  const [rescheduleFaculty, setRescheduleFaculty] = useState("");
  const [rescheduleReason, setRescheduleReason] = useState("Administrative adjustment");
  const [conflictWarnings, setConflictWarnings] = useState<string[]>([]);
  const [checkingConflict, setCheckingConflict] = useState(false);
  const [submittingReschedule, setSubmittingReschedule] = useState(false);

  // Load initial metadata
  useEffect(() => {
    async function init() {
      try {
        const [vRes, dRes, pRes, semRes, sRes, rRes, fRes] = await Promise.all([
          api.get("/scheduling/versions"),
          api.get("/academic/departments"),
          api.get("/academic/programmes"),
          api.get("/academic/semesters"),
          api.get("/academic/sections"),
          api.get("/campus/rooms"),
          api.get("/academic/faculty")
        ]);

        setVersions(vRes.data);
        setDepartments(dRes.data);
        setProgrammes(pRes.data);
        setSemesters(semRes.data);
        setSections(sRes.data);
        setRooms(rRes.data);
        setFacultyList(fRes.data);

        if (vRes.data.length > 0) {
          setSelectedVersion(vRes.data[0].id);
        }
        if (sRes.data.length > 0) {
          setSelectedSection(sRes.data[0].id);
        }
      } catch {
        setError("Failed to load timetable metadata.");
      }
    }
    init();
  }, []);

  // Dependent Filter logic:
  // Programme -> Semesters -> Sections
  const filteredProgrammes = selectedDept
    ? programmes.filter(p => p.department_id === selectedDept)
    : programmes;

  const filteredSemesters = selectedProg
    ? semesters.filter(s => s.programme_id === selectedProg)
    : semesters;

  const filteredSections = selectedSem
    ? sections.filter(s => s.semester_id === selectedSem)
    : (selectedProg ? sections.filter(s => s.programme_id === selectedProg) : sections);

  // Load classes when version or section changes
  async function loadClasses() {
    if (!selectedVersion || !selectedSection) return;
    setLoading(true);
    setError("");
    setSuccessMsg("");
    try {
      const response = await api.get(
        `/scheduling/versions/${selectedVersion}/section/${selectedSection}`
      );
      setClasses(response.data || []);
    } catch {
      setError("Unable to load timetable sessions for the selected section.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (selectedVersion && selectedSection) {
      loadClasses();
    }
  }, [selectedVersion, selectedSection]);

  // Generate Timetable for this Section independently
  async function handleGenerateSectionTimetable() {
    if (!selectedSection) {
      setError("Please select a target Section first.");
      return;
    }
    setGeneratingSection(true);
    setError("");
    setSuccessMsg("");
    try {
      const res = await api.post("/scheduling/generate", {
        section_id: selectedSection,
        semester_id: selectedSem || undefined,
        programme_id: selectedProg || undefined,
        mode: "HYBRID",
        priority_weight: 0.65,
        sjf_weight: 0.35,
        weekdays: [0, 1, 2, 3, 4, 5],
        time_limit_seconds: 30
      });

      if (res.data.status === "EMPTY") {
        setError("No active faculty assignments found for this section. Please create assignments first.");
        return;
      }

      if (res.data.status !== "OPTIMAL" && res.data.status !== "FEASIBLE") {
        const reasons = (res.data.unscheduled || []).map((u: any) => `${u.subject || u.assignment_id || 'Class'}: ${u.reason}`).filter(Boolean);
        setError(`The solver could not create a timetable (${res.data.status}). ${reasons.join(" | ") || "Check conflicting constraints."}`);
        return;
      }

      setSuccessMsg(`Timetable Version ${res.data.version_number} generated successfully for this section!`);

      // Refresh version list and auto-select newly generated version
      const vRes = await api.get("/scheduling/versions");
      setVersions(vRes.data);
      if (res.data.version_id) {
        setSelectedVersion(res.data.version_id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to generate timetable for the selected section.");
    } finally {
      setGeneratingSection(false);
    }
  }

  // Context Info derivation from loaded classes or selected section
  const currentSection = sections.find(s => s.id === selectedSection);
  const sampleClass = classes[0];
  const academicContext = {
    department: sampleClass?.department || "Academic Department",
    programme: sampleClass?.programme || (programmes.find(p => p.id === selectedProg)?.name || "Undergraduate Programme"),
    academic_year: sampleClass?.academic_year || "2026-2027",
    semester: sampleClass?.semester ? `Semester ${sampleClass.semester}` : (selectedSem ? `Semester ${semesters.find(s => s.id === selectedSem)?.number || ""}` : "Current Semester"),
    section: currentSection?.name || "A",
    section_code: currentSection?.section_code || "",
    section_display_name: currentSection?.display_name || ""
  };

  // PNG Generation & Authenticated Download (Blob Response)
  async function handleDownloadPNG() {
    if (!selectedVersion) {
      setError("Please select a timetable version first.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      let downloadUrl = "";
      let defaultFilename = `Timetable_v${selectedVersion}.png`;

      if (selectedSection) {
        downloadUrl = `/scheduling/versions/${selectedVersion}/section/${selectedSection}/download`;
        const secObj = sections.find(s => s.id === selectedSection);
        const secName = secObj ? secObj.name : "A";
        defaultFilename = `Timetable_${secObj?.section_code || `${academicContext.programme}_Sec${secName}`}.png`;
      } else {
        await api.post(`/scheduling/versions/${selectedVersion}/images`);
        const imagesList = await api.get(`/scheduling/versions/${selectedVersion}/images-list`);
        if (imagesList.data && imagesList.data.length > 0) {
          downloadUrl = imagesList.data[0].download_url;
          defaultFilename = imagesList.data[0].filename || defaultFilename;
        }
      }

      if (!downloadUrl) {
        setError("Please select a section to download its timetable PNG.");
        return;
      }

      const res = await api.get(downloadUrl, { responseType: "blob" });
      let filename = defaultFilename;
      const dispHeader = res.headers["content-disposition"];
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
      setSuccessMsg(`Downloaded ${filename} successfully!`);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to generate or download PNG timetable.");
    } finally {
      setLoading(false);
    }
  }

  // Open Reschedule Modal
  function openReschedule(session: TimetableEntry) {
    setRescheduleSession(session);
    setRescheduleDay(session.weekday);
    setRescheduleStart(session.start_minute);
    setRescheduleEnd(session.end_minute);
    setRescheduleRoom(session.room_id || "");
    setRescheduleFaculty(session.faculty_id || "");
    setConflictWarnings([]);
  }

  // Live conflict checking
  async function runConflictCheck() {
    if (!rescheduleSession || !selectedVersion) return;
    setCheckingConflict(true);
    try {
      const res = await api.post("/scheduling/check-conflict", {
        version_id: selectedVersion,
        class_id: rescheduleSession.id,
        new_weekday: Number(rescheduleDay),
        new_start_minute: Number(rescheduleStart),
        new_end_minute: Number(rescheduleEnd),
        new_room_id: rescheduleRoom || undefined,
        new_faculty_id: rescheduleFaculty || undefined
      });

      if (!res.data.valid) {
        setConflictWarnings(res.data.conflicts || ["A conflict was detected."]);
      } else {
        setConflictWarnings([]);
      }
    } catch {
      setConflictWarnings(["Conflict check failed. Please verify parameters."]);
    } finally {
      setCheckingConflict(false);
    }
  }

  // Submit manual reschedule
  async function submitReschedule() {
    if (!rescheduleSession || !selectedVersion) return;
    setSubmittingReschedule(true);
    setError("");
    try {
      const res = await api.post(`/scheduling/versions/${selectedVersion}/manual-reschedule`, {
        class_id: rescheduleSession.id,
        new_weekday: Number(rescheduleDay),
        new_start_minute: Number(rescheduleStart),
        new_end_minute: Number(rescheduleEnd),
        new_room_id: rescheduleRoom || undefined,
        new_faculty_id: rescheduleFaculty || undefined,
        reason: rescheduleReason
      });

      setSuccessMsg(`Rescheduled successfully! Created new Version ${res.data.new_version_number}.`);
      setRescheduleSession(null);

      // Refresh version list and select new version
      const vRes = await api.get("/scheduling/versions");
      setVersions(vRes.data);
      if (res.data.new_version_id) {
        setSelectedVersion(res.data.new_version_id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Manual rescheduling rejected due to constraint clashes.");
    } finally {
      setSubmittingReschedule(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Header & Context Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">University Timetable View</h2>
          <p className="text-sm text-slate-500 mt-1">
            Weekly grid schedule with complete academic context, room allocations, and manual clash-free rescheduling.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode("grid")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
              viewMode === "grid" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Weekly Grid
          </button>
          <button
            onClick={() => setViewMode("table")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
              viewMode === "table" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Tabular View
          </button>
          <button
            onClick={() => setWorkingDaysCount(workingDaysCount === 5 ? 6 : 5)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border ${
              workingDaysCount === 6
                ? "bg-indigo-50 border-indigo-300 text-indigo-700"
                : "bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100"
            }`}
            title="Toggle between 5-day (Mon-Fri) and 6-day (Mon-Sat) view"
          >
            {workingDaysCount === 6 ? "📅 6 Working Days (Mon–Sat)" : "📅 5 Working Days (Mon–Fri)"}
          </button>
          <button
            onClick={handleDownloadPNG}
            disabled={loading || classes.length === 0}
            className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
          >
            <Download size={14} />
            Download PNG
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-3.5 rounded-xl text-sm flex items-center gap-2">
          <AlertCircle size={16} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-3.5 rounded-xl text-sm flex items-center gap-2">
          <ShieldCheck size={16} className="shrink-0 text-emerald-600" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Filter Controls Panel */}
      <div className="panel bg-slate-50 border border-slate-200/80 p-4 rounded-xl space-y-3">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
          <Filter size={14} />
          Academic Scope & Version Filters
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-6 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Timetable Version</label>
            <select
              className="field text-xs py-1.5"
              value={selectedVersion}
              onChange={e => setSelectedVersion(e.target.value)}
            >
              {versions.map(v => (
                <option key={v.id} value={v.id}>
                  Version {v.version_number} ({v.status}) • {v.section_display_name || v.section_name || "All Sections"} • Score: {v.quality_score}%
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Department</label>
            <select
              className="field text-xs py-1.5"
              value={selectedDept}
              onChange={e => {
                setSelectedDept(e.target.value);
                setSelectedProg("");
                setSelectedSem("");
                setSelectedSection("");
              }}
            >
              <option value="">All Departments</option>
              {departments.map(d => (
                <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Programme</label>
            <select
              className="field text-xs py-1.5"
              value={selectedProg}
              onChange={e => {
                setSelectedProg(e.target.value);
                setSelectedSem("");
                setSelectedSection("");
              }}
            >
              <option value="">All Programmes</option>
              {filteredProgrammes.map(p => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.code})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Semester (Year)</label>
            <select
              className="field text-xs py-1.5"
              value={selectedSem}
              onChange={e => {
                setSelectedSem(e.target.value);
                setSelectedSection("");
              }}
            >
              <option value="">All Semesters</option>
              {filteredSemesters.map(s => {
                const progYear = Math.ceil(s.number / 2);
                return (
                  <option key={s.id} value={s.id}>
                    Semester {s.number} (Year {progYear})
                  </option>
                );
              })}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Section</label>
            <select
              className="field text-xs py-1.5 font-bold text-indigo-700"
              value={selectedSection}
              onChange={e => setSelectedSection(e.target.value)}
            >
              {filteredSections.map(s => (
                <option key={s.id} value={s.id}>
                  {s.display_name || (s.section_code ? `${s.section_code} (Section ${s.name})` : `Section ${s.name}`)} ({s.student_count} Students)
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={handleGenerateSectionTimetable}
              disabled={generatingSection || !selectedSection}
              className="w-full flex items-center justify-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white py-2 rounded-lg text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              <Play size={13} className={generatingSection ? "animate-spin" : ""} />
              {generatingSection ? "Generating..." : "Generate Section Schedule"}
            </button>
          </div>
        </div>
      </div>

      {/* FULL ACADEMIC CONTEXT BANNER (Per Requirement 12.3) */}
      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-5 rounded-2xl shadow-sm border border-slate-800">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-indigo-300 text-xs font-semibold uppercase tracking-wider">
              <span>{academicContext.academic_year}</span>
              <span>•</span>
              <span>{academicContext.semester}</span>
            </div>
            <div className="flex flex-wrap items-center gap-2.5">
              <h3 className="text-xl font-bold tracking-tight text-white">
                {academicContext.section_display_name || `${academicContext.programme} — Section ${academicContext.section}`}
              </h3>
              {academicContext.section_code && (
                <span className="bg-indigo-500/20 text-indigo-300 font-mono text-xs px-2 py-0.5 rounded border border-indigo-400/30">
                  {academicContext.section_code}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              Department of {academicContext.department}
            </p>
          </div>

          <div className="flex items-center gap-4 bg-white/10 px-4 py-2.5 rounded-xl backdrop-blur-sm text-xs">
            <div>
              <p className="text-slate-400">Total Weekly Classes</p>
              <p className="text-lg font-bold text-white">{classes.length}</p>
            </div>
            <div className="h-8 w-px bg-white/20" />
            <div>
              <p className="text-slate-400">Section Size</p>
              <p className="text-lg font-bold text-emerald-400">{currentSection?.student_count || 40}</p>
            </div>
          </div>
        </div>
      </div>

      {/* WEEKLY GRID VIEW */}
      {viewMode === "grid" ? (
        <div className="panel overflow-x-auto p-4">
          {(() => {
            const hasSaturday = classes.some(c => c.weekday === 5);
            const activeDays = (workingDaysCount === 6 || hasSaturday) ? [0, 1, 2, 3, 4, 5] : [0, 1, 2, 3, 4];
            return (
              <div className={activeDays.length === 6 ? "min-w-[1080px] grid grid-cols-6 gap-3" : "min-w-[900px] grid grid-cols-5 gap-3"}>
                {activeDays.map(dayIdx => {
                  const dayClasses = classes.filter(c => c.weekday === dayIdx);
                  dayClasses.sort((a, b) => a.start_minute - b.start_minute);

                  return (
                    <div key={dayIdx} className="space-y-3">
                      <div className={`border rounded-xl p-2.5 text-center ${dayIdx === 5 ? "bg-amber-50/90 border-amber-200" : "bg-indigo-50/80 border-indigo-100"}`}>
                        <p className={`font-bold text-sm ${dayIdx === 5 ? "text-amber-950" : "text-indigo-950"}`}>{DAYS[dayIdx]}</p>
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
                          dayClasses.map(c => {
                            const isLab = c.session_type === "LABORATORY";

                            return (
                              <div
                                key={c.id}
                                className={`p-3 rounded-xl border transition-all hover:shadow-md ${
                                  isLab
                                    ? "bg-purple-50/60 border-purple-200"
                                    : "bg-white border-slate-200"
                                } ${c.manual_override ? "ring-1 ring-amber-400" : ""}`}
                              >
                                <div className="flex items-start justify-between gap-1">
                                  <div>
                                    <span className="inline-block text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700">
                                      {c.subject_code || "CS"}
                                    </span>
                                    <h4 className="font-bold text-xs text-slate-900 mt-1 line-clamp-1" title={c.subject}>
                                      {c.subject}
                                    </h4>
                                  </div>
                                  <button
                                    onClick={() => openReschedule(c)}
                                    title="Reschedule Session"
                                    className="text-slate-400 hover:text-indigo-600 p-1 rounded hover:bg-slate-100"
                                  >
                                    <Edit2 size={13} />
                                  </button>
                                </div>

                                <div className="mt-2.5 space-y-1 text-[11px] text-slate-600">
                                  <div className="flex items-center gap-1.5">
                                    <Clock size={12} className="text-slate-400 shrink-0" />
                                    <span>{c.start} - {c.end} ({c.duration || 60}m)</span>
                                  </div>
                                  <div className="flex items-center gap-1.5">
                                    <User size={12} className="text-slate-400 shrink-0" />
                                    <span className="truncate">{c.faculty}</span>
                                  </div>
                                  <div className="flex items-center gap-1.5 text-blue-700 font-medium">
                                    <MapPin size={12} className="shrink-0" />
                                    <span className="truncate">{c.room} ({c.building})</span>
                                  </div>
                                </div>

                                {c.manual_override && (
                                  <div className="mt-2 text-[10px] font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded">
                                    Manual Override
                                  </div>
                                )}
                              </div>
                            );
                          })
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })()}
        </div>
      ) : (
        /* TABULAR LIST VIEW */
        <div className="panel overflow-x-auto">
          <table className="table min-w-[900px]">
            <thead>
              <tr>
                <th>Day</th>
                <th>Time Window</th>
                <th>Subject & Code</th>
                <th>Faculty</th>
                <th>Classroom</th>
                <th>Type</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {classes.map(c => (
                <tr key={c.id}>
                  <td className="font-semibold">{DAYS[c.weekday]}</td>
                  <td>{c.start} - {c.end}</td>
                  <td>
                    <span className="font-bold text-indigo-700">{c.subject_code}</span>: {c.subject}
                  </td>
                  <td>{c.faculty}</td>
                  <td>{c.room} ({c.building})</td>
                  <td>
                    <span className={`badge ${c.session_type === "LABORATORY" ? "badge-purple" : "badge-blue"}`}>
                      {c.session_type}
                    </span>
                  </td>
                  <td>
                    <button
                      onClick={() => openReschedule(c)}
                      className="text-indigo-600 hover:text-indigo-800 text-xs font-semibold flex items-center gap-1"
                    >
                      <Edit2 size={12} />
                      Reschedule
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* RESCHEDULING MODAL (SECTION 9) */}
      {rescheduleSession && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="font-bold text-lg text-slate-900">Reschedule Timetable Session</h3>
                <p className="text-xs text-slate-500">
                  Move session with instant DBMS conflict checking & version branching.
                </p>
              </div>
              <button
                onClick={() => setRescheduleSession(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-3 bg-indigo-50/70 rounded-xl text-xs space-y-1">
              <p className="font-semibold text-indigo-900">{rescheduleSession.subject_code}: {rescheduleSession.subject}</p>
              <p className="text-slate-600">Current: {DAYS[rescheduleSession.weekday]} at {rescheduleSession.start} - {rescheduleSession.end} in {rescheduleSession.room}</p>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Target Day</label>
                <select
                  className="field py-1.5"
                  value={rescheduleDay}
                  onChange={e => setRescheduleDay(Number(e.target.value))}
                >
                  {DAYS.slice(0, 6).map((d, idx) => (
                    <option key={d} value={idx}>{d}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Start Minute</label>
                  <select
                    className="field py-1.5"
                    value={rescheduleStart}
                    onChange={e => {
                      const s = Number(e.target.value);
                      setRescheduleStart(s);
                      setRescheduleEnd(s + (rescheduleSession.duration || 60));
                    }}
                  >
                    {[480, 540, 600, 660, 720, 780, 840, 900, 960, 1020].map(m => (
                      <option key={m} value={m}>
                        {Math.floor(m / 60).toString().padStart(2, "0")}:{(m % 60).toString().padStart(2, "0")}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">End Minute</label>
                  <input
                    type="text"
                    disabled
                    className="field py-1.5 bg-slate-100"
                    value={`${Math.floor(rescheduleEnd / 60).toString().padStart(2, "0")}:${(rescheduleEnd % 60).toString().padStart(2, "0")}`}
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Change Classroom (Optional)</label>
                <select
                  className="field py-1.5"
                  value={rescheduleRoom}
                  onChange={e => setRescheduleRoom(e.target.value)}
                >
                  <option value="">Keep Current Room ({rescheduleSession.room})</option>
                  {rooms.map(r => (
                    <option key={r.id} value={r.id}>
                      {r.name} ({r.room_type}, Cap: {r.capacity})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Change Faculty (Optional)</label>
                <select
                  className="field py-1.5"
                  value={rescheduleFaculty}
                  onChange={e => setRescheduleFaculty(e.target.value)}
                >
                  <option value="">Keep Current Faculty ({rescheduleSession.faculty})</option>
                  {facultyList.map(f => (
                    <option key={f.id} value={f.id}>
                      {f.full_name} ({f.faculty_id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Reason for Rescheduling</label>
                <input
                  className="field py-1.5"
                  value={rescheduleReason}
                  onChange={e => setRescheduleReason(e.target.value)}
                  placeholder="e.g. Faculty medical leave / room maintenance"
                />
              </div>

              {/* Conflict Warnings */}
              {conflictWarnings.length > 0 && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl space-y-1">
                  <div className="flex items-center gap-1.5 text-red-800 font-bold">
                    <AlertCircle size={14} />
                    <span>Conflict Detected! Cannot Reschedule to this slot:</span>
                  </div>
                  {conflictWarnings.map((w, i) => (
                    <p key={i} className="text-red-700 text-[11px]">• {w}</p>
                  ))}
                </div>
              )}
            </div>

            <div className="flex items-center justify-between pt-3 border-t">
              <button
                type="button"
                onClick={runConflictCheck}
                disabled={checkingConflict}
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
              >
                <RefreshCw size={12} className={checkingConflict ? "animate-spin" : ""} />
                Check Conflicts
              </button>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setRescheduleSession(null)}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={submitReschedule}
                  disabled={submittingReschedule || conflictWarnings.length > 0}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-1.5 rounded-lg text-xs font-semibold transition-all disabled:opacity-50"
                >
                  {submittingReschedule ? "Saving..." : "Confirm Reschedule"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
