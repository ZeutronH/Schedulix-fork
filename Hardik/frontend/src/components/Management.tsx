import { useEffect, useState } from "react";
import {
  Plus, RefreshCw, Search,
  Network, Mail,
  Send, CheckCircle2, AlertTriangle, ArrowRight, Trash2,
  Edit3, ArrowLeftRight, FileText, X, Calendar,
  BookOpen, KeyRound
} from "lucide-react";

import api from "../api";
import type {
  Department, Programme, Section, Faculty, Subject,
  Room, Building, Floor, AcademicYear, Semester, Student
} from "../types";

interface Props {
  type: string;
}

export default function Management({ type }: Props) {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState<any | null>(null);

  // Common DB dropdown datasets
  const [departments, setDepartments] = useState<Department[]>([]);
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [academicYears, setAcademicYears] = useState<AcademicYear[]>([]);
  const [semesters, setSemesters] = useState<Semester[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [facultyList, setFacultyList] = useState<Faculty[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [floors, setFloors] = useState<Floor[]>([]);
  const [buildings, setBuildings] = useState<Building[]>([]);

  // Generic form state
  const [form, setForm] = useState<Record<string, any>>({});

  // Filter state for Students & Subjects tabs
  const [filterProg, setFilterProg] = useState("");
  const [filterSem, setFilterSem] = useState("");
  const [filterSec, setFilterSec] = useState("");

  // Student Transfer Modal State
  const [transferStudent, setTransferStudent] = useState<Student | null>(null);
  const [transferTargetSection, setTransferTargetSection] = useState("");
  const [transferLoading, setTransferLoading] = useState(false);

  // Student Assignment View Modal State
  const [assignmentStudent, setAssignmentStudent] = useState<Student | null>(null);
  const [assignmentDetails, setAssignmentDetails] = useState<any | null>(null);
  const [assignmentLoading, setAssignmentLoading] = useState(false);

  // Campus Route Planner State
  const [routeRoomA, setRouteRoomA] = useState("");
  const [routeRoomB, setRouteRoomB] = useState("");
  const [routeResult, setRouteResult] = useState<any>(null);
  const [routingLoading, setRoutingLoading] = useState(false);

  // Email dispatch state
  const [versions, setVersions] = useState<any[]>([]);
  const [selectedVersionForEmail, setSelectedVersionForEmail] = useState("");
  const [smtpStatus, setSmtpStatus] = useState<any>(null);
  const [sendingEmail, setSendingEmail] = useState(false);

  // Faculty Eligibility & Workload state
  const [eligibilityFaculty, setEligibilityFaculty] = useState<any | null>(null);
  const [selectedEligibleSubjects, setSelectedEligibleSubjects] = useState<string[]>([]);
  const [selectedEligibleSemesters, setSelectedEligibleSemesters] = useState<number[]>([]);
  const [crossDeptApproved, setCrossDeptApproved] = useState(false);
  const [savingEligibility, setSavingEligibility] = useState(false);
  const [workloadData, setWorkloadData] = useState<any | null>(null);

  // Load supporting dropdown data
  async function loadDropdowns() {
    try {
      const [dRes, pRes, ayRes, semRes, secRes, fRes, sRes, rRes, flRes, bRes] = await Promise.all([
        api.get("/academic/departments"),
        api.get("/academic/programmes"),
        api.get("/academic/academic-years"),
        api.get("/academic/semesters"),
        api.get("/academic/sections"),
        api.get("/academic/faculty"),
        api.get("/academic/subjects"),
        api.get("/campus/rooms"),
        api.get("/campus/floors"),
        api.get("/campus/buildings")
      ]);
      setDepartments(dRes.data || []);
      setProgrammes(pRes.data || []);
      setAcademicYears(ayRes.data || []);
      setSemesters(semRes.data || []);
      setSections(secRes.data || []);
      setFacultyList(fRes.data || []);
      setSubjects(sRes.data || []);
      setRooms(rRes.data || []);
      setFloors(flRes.data || []);
      setBuildings(bRes.data || []);
    } catch {
      // Ignore background dropdown load error
    }
  }

  // Primary loader for each tab
  async function load() {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      if (type === "Departments") {
        const res = await api.get("/academic/departments");
        setItems(res.data || []);
      } else if (type === "Programmes") {
        const res = await api.get("/academic/programmes");
        setItems(res.data || []);
      } else if (type === "Academic Years") {
        const res = await api.get("/academic/academic-years");
        setItems(res.data || []);
      } else if (type === "Semesters") {
        const url = filterProg ? `/academic/semesters?programme_id=${filterProg}` : "/academic/semesters";
        const res = await api.get(url);
        setItems(res.data || []);
      } else if (type === "Sections") {
        let url = "/academic/sections";
        const params = new URLSearchParams();
        if (filterProg) params.append("programme_id", filterProg);
        if (filterSem) params.append("semester_id", filterSem);
        if (params.toString()) url += `?${params.toString()}`;
        const res = await api.get(url);
        setItems(res.data || []);
      } else if (type === "Students" || type === "Students & Enrolments") {
        let url = "/academic/students";
        const params = new URLSearchParams();
        if (filterProg) params.append("programme_id", filterProg);
        if (filterSem) params.append("semester_id", filterSem);
        if (filterSec) params.append("section_id", filterSec);
        if (params.toString()) url += `?${params.toString()}`;
        const res = await api.get(url);
        setItems(res.data || []);
      } else if (type === "Faculty") {
        const res = await api.get("/academic/faculty");
        setItems(res.data || []);
      } else if (type === "Faculty Workload") {
        const res = await api.get("/academic/faculty-workload/overview");
        setItems(res.data?.faculty_workload || []);
        setWorkloadData(res.data);
      } else if (type === "Subjects") {
        let url = "/academic/subjects";
        const params = new URLSearchParams();
        if (filterProg) params.append("programme_id", filterProg);
        if (filterSem) {
          const matchedSem = semesters.find(s => s.id === filterSem);
          if (matchedSem) params.append("semester_number", String(matchedSem.number));
        }
        if (params.toString()) url += `?${params.toString()}`;
        const res = await api.get(url);
        setItems(res.data || []);
      } else if (type === "Faculty Assignments") {
        const res = await api.get("/academic/assignments");
        setItems(res.data || []);
      } else if (type === "Campus" || type === "Classrooms") {
        const res = await api.get("/campus/rooms");
        setItems(res.data || []);
      } else if (type === "Availability") {
        const res = await api.get("/academic/faculty");
        setItems(res.data || []);
      } else if (type === "Email Notifications") {
        const [hRes, sRes, vRes] = await Promise.all([
          api.get("/notifications/history"),
          api.get("/notifications/status"),
          api.get("/scheduling/versions")
        ]);
        setItems(hRes.data || []);
        setSmtpStatus(sRes.data);
        setVersions(vRes.data || []);
        if (vRes.data.length > 0) setSelectedVersionForEmail(vRes.data[0].id);
      } else if (type === "Audit Logs") {
        const res = await api.get("/audit/logs?limit=100");
        setItems(res.data || []);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to load ${type}.`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setItems([]);
    setForm({});
    setShowForm(false);
    setEditItem(null);
    setSearch("");
    loadDropdowns();
    load();
  }, [type, filterProg, filterSem, filterSec]);

  // Handle Form Submission (Create or Edit)
  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      if (editItem) {
        // Edit mode
        if (type === "Programmes") {
          await api.put(`/academic/programmes/${editItem.id}`, {
            name: form.name?.trim(),
            code: form.code?.trim().toUpperCase(),
            duration_years: Number(form.duration_years || 4),
            department_id: form.department_id
          });
          setMessage(`Programme '${form.name}' updated successfully.`);
        } else if (type === "Subjects") {
          await api.put(`/academic/subjects/${editItem.id}`, {
            name: form.name?.trim(),
            code: form.code?.trim().toUpperCase(),
            session_type: form.session_type || "LECTURE",
            default_duration: Number(form.default_duration || 60),
            department_id: form.department_id,
            programme_id: form.programme_id || null,
            semester_number: form.semester_number ? Number(form.semester_number) : null
          });
          setMessage(`Subject '${form.name}' updated successfully.`);
        } else if (type === "Faculty") {
          await api.put(`/academic/faculty/${editItem.id}`, {
            full_name: form.full_name?.trim(),
            email: form.email?.trim(),
            department_id: form.department_id,
            phone: form.phone?.trim() || null,
            whatsapp_number: form.whatsapp_number?.trim() || null,
            designation: form.designation?.trim(),
            highest_qualification: form.highest_qualification?.trim(),
            specialisation: form.specialisation?.trim(),
            max_classes_per_day: Number(form.max_classes_per_day || 4),
            max_classes_per_week: Number(form.max_classes_per_week || 18),
            max_consecutive_hours: Number(form.max_consecutive_hours || 2),
            min_break_minutes: Number(form.min_break_minutes || 15),
            cross_department_approved: Boolean(form.cross_department_approved)
          });
          setMessage(`Faculty member '${form.full_name}' updated successfully.`);
        }
        setEditItem(null);
      } else {
        // Create mode
        if (type === "Departments") {
          await api.post("/academic/departments", {
            name: form.name?.trim(),
            code: form.code?.trim().toUpperCase(),
            description: form.description
          });
          setMessage(`Department '${form.name}' created successfully.`);
        } else if (type === "Programmes") {
          await api.post("/academic/programmes", {
            department_id: form.department_id,
            name: form.name?.trim(),
            code: form.code?.trim().toUpperCase(),
            duration_years: Number(form.duration_years || 4)
          });
          setMessage(`Programme '${form.name}' created successfully.`);
        } else if (type === "Academic Years") {
          await api.post("/academic/academic-years", {
            name: form.name?.trim(),
            start_date: form.start_date,
            end_date: form.end_date
          });
          setMessage(`Academic Year '${form.name}' created successfully.`);
        } else if (type === "Semesters") {
          await api.post("/academic/semesters", null, {
            params: {
              programme_id: form.programme_id,
              academic_year_id: form.academic_year_id,
              number: Number(form.number)
            }
          });
          setMessage(`Semester ${form.number} created successfully.`);
        } else if (type === "Sections") {
          await api.post("/academic/sections", {
            programme_id: form.programme_id,
            semester_id: form.semester_id,
            name: form.name?.trim().toUpperCase(),
            student_count: Number(form.student_count || 0)
          });
          setMessage(`Section '${form.name}' created successfully.`);
        } else if (type === "Students" || type === "Students & Enrolments") {
          const res = await api.post("/academic/students", {
            full_name: form.full_name?.trim(),
            email: form.email?.trim(),
            admission_year: Number(form.admission_year || 2026),
            phone: form.phone?.trim() || null,
            whatsapp_number: form.whatsapp_number?.trim() || null,
            department_id: form.department_id || null,
            programme_id: form.programme_id || null,
            section_id: form.section_id || null
          });
          setMessage(`Student registered with ID: ${res.data.student_id}${form.section_id ? ' and enrolled in section.' : '.'}`);
        } else if (type === "Faculty") {
          const res = await api.post("/academic/faculty", {
            department_id: form.department_id,
            full_name: form.full_name?.trim(),
            email: form.email?.trim(),
            phone: form.phone?.trim() || null,
            whatsapp_number: form.whatsapp_number?.trim() || null,
            designation: form.designation?.trim() || "Assistant Professor",
            highest_qualification: form.highest_qualification?.trim() || "Ph.D.",
            specialisation: form.specialisation?.trim() || "Computer Science",
            max_classes_per_day: Number(form.max_classes_per_day || 4),
            max_classes_per_week: Number(form.max_classes_per_week || 18),
            max_consecutive_hours: Number(form.max_consecutive_hours || 2),
            min_break_minutes: Number(form.min_break_minutes || 15),
            cross_department_approved: Boolean(form.cross_department_approved)
          });
          setMessage(`Faculty registered with ID: ${res.data.faculty_id}`);
        } else if (type === "Subjects") {
          await api.post("/academic/subjects", {
            department_id: form.department_id,
            programme_id: form.programme_id || null,
            semester_number: form.semester_number ? Number(form.semester_number) : null,
            code: form.code?.trim().toUpperCase(),
            name: form.name?.trim(),
            session_type: form.session_type || "LECTURE",
            default_duration: Number(form.default_duration || 60)
          });
          setMessage(`Subject '${form.name}' (${form.code}) created successfully.`);
        } else if (type === "Faculty Assignments") {
          await api.post("/academic/assignments", {
            faculty_id: form.faculty_id,
            subject_id: form.subject_id,
            section_id: form.section_id,
            sessions_per_week: Number(form.sessions_per_week || 3),
            duration_minutes: Number(form.duration_minutes || 60),
            priority: Number(form.priority || 7),
            required_capacity: Number(form.required_capacity || 40),
            required_room_type: form.required_room_type || "CLASSROOM"
          });
          setMessage("Faculty assignment created successfully.");
        } else if (type === "Campus" || type === "Classrooms") {
          await api.post("/campus/rooms", {
            floor_id: form.floor_id,
            name: form.name?.trim().toUpperCase(),
            room_type: form.room_type || "CLASSROOM",
            capacity: Number(form.capacity || 50),
            equipment: form.equipment ? form.equipment.split(",").map((s: string) => s.trim()) : ["Whiteboard"]
          });
          setMessage("Classroom created successfully.");
        }
      }

      setForm({});
      setShowForm(false);
      loadDropdowns();
      load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Action failed. Please check input fields.");
    }
  }

  // Safe Deletion Handlers
  async function handleDeleteProgramme(id: string, name: string) {
    if (!confirm(`Are you sure you want to delete programme '${name}'? This will fail safely if dependent semesters, subjects, or students exist.`)) return;
    setError("");
    setMessage("");
    try {
      const res = await api.delete(`/academic/programmes/${id}`);
      setMessage(res.data.message || `Programme '${name}' deleted.`);
      loadDropdowns();
      load();
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to delete programme '${name}'.`);
    }
  }

  async function handleDeleteSubject(id: string, name: string) {
    if (!confirm(`Are you sure you want to delete subject '${name}'? Deletion will be rejected if it is referenced by faculty assignments or timetable classes.`)) return;
    setError("");
    setMessage("");
    try {
      const res = await api.delete(`/academic/subjects/${id}`);
      setMessage(res.data.message || `Subject '${name}' deleted.`);
      loadDropdowns();
      load();
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to delete subject '${name}'.`);
    }
  }

  async function handleDeleteSemester(id: string, num: number) {
    if (!confirm(`Are you sure you want to delete Semester ${num}?`)) return;
    setError("");
    setMessage("");
    try {
      const res = await api.delete(`/academic/semesters/${id}`);
      setMessage(res.data.message || `Semester ${num} deleted.`);
      loadDropdowns();
      load();
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to delete Semester ${num}.`);
    }
  }

  async function handleDeleteSection(id: string, name: string) {
    if (!confirm(`Are you sure you want to delete Section ${name}?`)) return;
    setError("");
    setMessage("");
    try {
      const res = await api.delete(`/academic/sections/${id}`);
      setMessage(res.data.message || `Section ${name} deleted.`);
      loadDropdowns();
      load();
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to delete Section ${name}.`);
    }
  }

  async function handleDeleteStudent(id: string, name: string) {
    if (!confirm(`Are you sure you want to delete student '${name}'?`)) return;
    setError("");
    setMessage("");
    try {
      const res = await api.delete(`/academic/students/${id}`);
      setMessage(res.data.message || `Student '${name}' deleted.`);
      loadDropdowns();
      load();
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to delete student '${name}'.`);
    }
  }

  // Activate Academic Year
  async function handleActivateAcademicYear(id: string, name: string) {
    setError("");
    setMessage("");
    try {
      await api.post(`/academic/academic-years/${id}/activate`);
      setMessage(`Academic Year '${name}' activated successfully.`);
      loadDropdowns();
      load();
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to activate academic year.`);
    }
  }

  // Open Edit Mode
  function startEdit(item: any) {
    setEditItem(item);
    setForm({ ...item });
    setShowForm(true);
  }

  // Student Transfer
  async function submitStudentTransfer(e: React.FormEvent) {
    e.preventDefault();
    if (!transferStudent || !transferTargetSection) return;
    setTransferLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await api.post(`/academic/students/${transferStudent.id}/transfer`, {
        new_section_id: transferTargetSection
      });
      setMessage(res.data.message || `Student ${transferStudent.full_name} transferred successfully.`);
      setTransferStudent(null);
      setTransferTargetSection("");
      loadDropdowns();
      load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Student transfer failed.");
    } finally {
      setTransferLoading(false);
    }
  }

  // Student Assignment View
  async function viewStudentAssignment(student: Student) {
    setAssignmentStudent(student);
    setAssignmentDetails(null);
    setAssignmentLoading(true);
    try {
      const res = await api.get(`/academic/students/${student.id}/assignment`);
      setAssignmentDetails(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load academic assignment.");
    } finally {
      setAssignmentLoading(false);
    }
  }

  // Toggle Assignment Active/Inactive
  async function toggleAssignment(id: string) {
    try {
      await api.patch(`/academic/assignments/${id}/toggle`);
      load();
    } catch {
      setError("Failed to toggle assignment status.");
    }
  }

  // Delete Assignment
  async function deleteAssignment(id: string) {
    if (!confirm("Are you sure you want to delete this faculty assignment?")) return;
    try {
      await api.delete(`/academic/assignments/${id}`);
      load();
    } catch {
      setError("Failed to delete assignment.");
    }
  }

  function openEligibilityModal(fac: any) {
    setEligibilityFaculty(fac);
    setSelectedEligibleSubjects(fac.eligible_subject_ids || []);
    setSelectedEligibleSemesters(fac.eligible_semesters || []);
    setCrossDeptApproved(Boolean(fac.cross_department_approved));
  }

  async function handleSaveEligibility() {
    if (!eligibilityFaculty) return;
    setSavingEligibility(true);
    setError("");
    setMessage("");
    try {
      await api.post(`/academic/faculty/${eligibilityFaculty.id}/eligibility`, {
        subject_ids: selectedEligibleSubjects,
        eligible_semesters: selectedEligibleSemesters,
        cross_department_approved: crossDeptApproved
      });
      setMessage(`Teaching eligibility configured successfully for ${eligibilityFaculty.full_name}.`);
      setEligibilityFaculty(null);
      load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to update teaching eligibility.");
    } finally {
      setSavingEligibility(false);
    }
  }

  // Route between rooms using NetworkX Dijkstra
  async function calculateRoute() {
    if (!routeRoomA || !routeRoomB) return;
    setRoutingLoading(true);
    setRouteResult(null);
    try {
      const res = await api.get(`/campus/route-between-rooms?source_room_id=${routeRoomA}&target_room_id=${routeRoomB}`);
      setRouteResult(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Unable to calculate campus path between rooms.");
    } finally {
      setRoutingLoading(false);
    }
  }

  // Dispatch Timetable Emails
  async function dispatchEmails() {
    if (!selectedVersionForEmail) return;
    setSendingEmail(true);
    setError("");
    setMessage("");
    try {
      const res = await api.post(`/notifications/send/${selectedVersionForEmail}`);
      setMessage(`Dispatched ${res.data.sent} notification emails with PNG attachments.`);
      load();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to dispatch timetable emails.");
    } finally {
      setSendingEmail(false);
    }
  }

  async function handleResetFacultyPassword(faculty: any) {
    const newPass = prompt(`Reset password for ${faculty.full_name} (${faculty.faculty_id}).\nEnter new password:`, "schedulix2026");
    if (!newPass) return;
    try {
      await api.post(`/academic/faculty/${faculty.id}/reset-password`, { new_password: newPass });
      setMessage(`Password updated successfully for ${faculty.full_name}.`);
      setTimeout(() => setMessage(""), 4000);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to reset faculty password.");
    }
  }

  const filteredItems = items.filter(item =>
    Object.values(item).some(v =>
      String(v ?? "").toLowerCase().includes(search.toLowerCase())
    )
  );

  // Form dependent lists
  const formFilteredSemesters = form.programme_id
    ? semesters.filter(s => s.programme_id === form.programme_id)
    : semesters;

  const formFilteredSections = form.semester_id
    ? sections.filter(s => s.semester_id === form.semester_id)
    : (form.programme_id ? sections.filter(s => s.programme_id === form.programme_id) : sections);

  return (
    <div className="space-y-6">
      {/* Tab Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">{type} Management</h2>
          <p className="text-sm text-slate-500 mt-1">
            Database-backed academic hierarchy & entity management with strict constraint validation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {["Departments", "Programmes", "Academic Years", "Semesters", "Sections", "Students", "Students & Enrolments", "Faculty", "Subjects", "Faculty Assignments", "Campus", "Classrooms"].includes(type) && (
            <button
              onClick={() => {
                if (showForm) {
                  setShowForm(false);
                  setEditItem(null);
                  setForm({});
                } else {
                  setForm({});
                  setEditItem(null);
                  setShowForm(true);
                }
              }}
              className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-all"
            >
              <Plus size={15} />
              {showForm ? "Cancel" : `Add ${type.replace(/s$/, "").replace("Students & Enrolment", "Student")}`}
            </button>
          )}
          <button
            onClick={load}
            disabled={loading}
            className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-all"
            title="Refresh"
          >
            <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-3.5 rounded-xl text-sm flex items-center gap-2">
          <AlertTriangle size={16} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {message && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-3.5 rounded-xl text-sm flex items-center gap-2">
          <CheckCircle2 size={16} className="shrink-0 text-emerald-600" />
          <span>{message}</span>
        </div>
      )}

      {/* FILTER BAR FOR STUDENTS, SUBJECTS, SECTIONS, SEMESTERS */}
      {["Students", "Students & Enrolments", "Subjects", "Sections", "Semesters"].includes(type) && (
        <div className="panel bg-slate-50 border border-slate-200/80 p-3.5 rounded-xl flex flex-wrap items-center gap-3 text-xs">
          <span className="font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            Filter Scope:
          </span>

          <div>
            <select
              className="field py-1 text-xs"
              value={filterProg}
              onChange={e => {
                setFilterProg(e.target.value);
                setFilterSem("");
                setFilterSec("");
              }}
            >
              <option value="">All Programmes</option>
              {programmes.map(p => (
                <option key={p.id} value={p.id}>{p.name} ({p.code})</option>
              ))}
            </select>
          </div>

          {["Students", "Students & Enrolments", "Subjects", "Sections"].includes(type) && (
            <div>
              <select
                className="field py-1 text-xs"
                value={filterSem}
                onChange={e => {
                  setFilterSem(e.target.value);
                  setFilterSec("");
                }}
              >
                <option value="">All Semesters</option>
                {semesters
                  .filter(s => !filterProg || s.programme_id === filterProg)
                  .map(s => (
                    <option key={s.id} value={s.id}>
                      Semester {s.number} (Year {Math.ceil(s.number / 2)})
                    </option>
                  ))}
              </select>
            </div>
          )}

          {["Students", "Students & Enrolments"].includes(type) && (
            <div>
              <select
                className="field py-1 text-xs"
                value={filterSec}
                onChange={e => setFilterSec(e.target.value)}
              >
                <option value="">All Sections</option>
                {sections
                  .filter(sec => (!filterSem || sec.semester_id === filterSem) && (!filterProg || sec.programme_id === filterProg))
                  .map(sec => (
                    <option key={sec.id} value={sec.id}>
                      {sec.display_name || (sec.section_code ? `${sec.section_code} (Section ${sec.name})` : `Section ${sec.name}`)}
                    </option>
                  ))}
              </select>
            </div>
          )}

          {(filterProg || filterSem || filterSec) && (
            <button
              onClick={() => {
                setFilterProg("");
                setFilterSem("");
                setFilterSec("");
              }}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold underline ml-auto"
            >
              Clear Filters
            </button>
          )}
        </div>
      )}

      {/* CREATION & EDIT MODAL / INLINE FORM */}
      {showForm && (
        <div className="panel bg-slate-50 border border-slate-200 p-5 rounded-2xl shadow-sm">
          <h3 className="font-bold text-sm text-slate-900 mb-3">
            {editItem ? `Edit ${type.replace(/s$/, "")}` : `Create New ${type.replace(/s$/, "").replace("Students & Enrolment", "Student")}`}
          </h3>
          <form onSubmit={handleCreate} className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            {type === "Departments" && (
              <>
                <div>
                  <label className="block font-semibold mb-1">Department Name *</label>
                  <input
                    required
                    className="field py-1.5"
                    placeholder="Computer Science & Engineering"
                    value={form.name || ""}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Department Code *</label>
                  <input
                    required
                    className="field py-1.5"
                    placeholder="CSE"
                    value={form.code || ""}
                    onChange={e => setForm({ ...form, code: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Description</label>
                  <input
                    className="field py-1.5"
                    placeholder="Optional description"
                    value={form.description || ""}
                    onChange={e => setForm({ ...form, description: e.target.value })}
                  />
                </div>
              </>
            )}

            {type === "Programmes" && (
              <>
                <div>
                  <label className="block font-semibold mb-1">Department *</label>
                  <select
                    required
                    className="field py-1.5"
                    value={form.department_id || ""}
                    onChange={e => setForm({ ...form, department_id: e.target.value })}
                  >
                    <option value="">Select Department</option>
                    {departments.map(d => (
                      <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Programme Name *</label>
                  <input
                    required
                    className="field py-1.5"
                    placeholder="B.Tech Computer Science"
                    value={form.name || ""}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Programme Code *</label>
                  <input
                    required
                    className="field py-1.5"
                    placeholder="BTECH-CSE"
                    value={form.code || ""}
                    onChange={e => setForm({ ...form, code: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Duration (Years) *</label>
                  <input
                    required
                    type="number"
                    min="1"
                    max="10"
                    className="field py-1.5"
                    value={form.duration_years || 4}
                    onChange={e => setForm({ ...form, duration_years: e.target.value })}
                  />
                </div>
              </>
            )}

            {type === "Academic Years" && (
              <>
                <div>
                  <label className="block font-semibold mb-1">Year Name *</label>
                  <input
                    required
                    className="field py-1.5"
                    placeholder="2026-2027"
                    value={form.name || ""}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Start Date *</label>
                  <input
                    required
                    type="date"
                    className="field py-1.5"
                    value={form.start_date || ""}
                    onChange={e => setForm({ ...form, start_date: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">End Date *</label>
                  <input
                    required
                    type="date"
                    className="field py-1.5"
                    value={form.end_date || ""}
                    onChange={e => setForm({ ...form, end_date: e.target.value })}
                  />
                </div>
              </>
            )}

            {type === "Semesters" && (
              <>
                <div>
                  <label className="block font-semibold mb-1">Programme *</label>
                  <select
                    required
                    className="field py-1.5"
                    value={form.programme_id || ""}
                    onChange={e => setForm({ ...form, programme_id: e.target.value })}
                  >
                    <option value="">Select Programme</option>
                    {programmes.map(p => (
                      <option key={p.id} value={p.id}>{p.name} ({p.code})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Academic Year *</label>
                  <select
                    required
                    className="field py-1.5"
                    value={form.academic_year_id || ""}
                    onChange={e => setForm({ ...form, academic_year_id: e.target.value })}
                  >
                    <option value="">Select Academic Year</option>
                    {academicYears.map(ay => (
                      <option key={ay.id} value={ay.id}>{ay.name} {ay.active ? '(Active)' : ''}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Semester Number (1-12) *</label>
                  <input
                    required
                    type="number"
                    min="1"
                    max="12"
                    className="field py-1.5"
                    placeholder="1"
                    value={form.number || 1}
                    onChange={e => setForm({ ...form, number: e.target.value })}
                  />
                  <span className="text-[10px] text-slate-500">
                    Programme Year will be: Year {Math.ceil(Number(form.number || 1) / 2)}
                  </span>
                </div>
              </>
            )}

            {type === "Sections" && (
              <>
                <div>
                  <label className="block font-semibold mb-1">Programme *</label>
                  <select
                    required
                    className="field py-1.5"
                    value={form.programme_id || ""}
                    onChange={e => setForm({ ...form, programme_id: e.target.value, semester_id: "" })}
                  >
                    <option value="">Select Programme</option>
                    {programmes.map(p => (
                      <option key={p.id} value={p.id}>{p.name} ({p.code})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Semester *</label>
                  <select
                    required
                    className="field py-1.5"
                    value={form.semester_id || ""}
                    onChange={e => setForm({ ...form, semester_id: e.target.value })}
                  >
                    <option value="">Select Semester</option>
                    {formFilteredSemesters.map(s => (
                      <option key={s.id} value={s.id}>
                        Semester {s.number} (Year {Math.ceil(s.number / 2)})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Section Name *</label>
                  <input
                    required
                    className="field py-1.5"
                    placeholder="A"
                    value={form.name || ""}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Student Capacity *</label>
                  <input
                    required
                    type="number"
                    min="0"
                    className="field py-1.5"
                    value={form.student_count || 40}
                    onChange={e => setForm({ ...form, student_count: e.target.value })}
                  />
                </div>
              </>
            )}

            {(type === "Students" || type === "Students & Enrolments") && (
              <>
                <div>
                  <label className="block font-semibold mb-1">Full Name *</label>
                  <input
                    required
                    className="field py-1.5"
                    placeholder="Student Full Name"
                    value={form.full_name || ""}
                    onChange={e => setForm({ ...form, full_name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Email Address *</label>
                  <input
                    required
                    type="email"
                    className="field py-1.5"
                    placeholder="student@example.edu"
                    value={form.email || ""}
                    onChange={e => setForm({ ...form, email: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Admission Year *</label>
                  <input
                    required
                    type="number"
                    className="field py-1.5"
                    value={form.admission_year || 2026}
                    onChange={e => setForm({ ...form, admission_year: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Department</label>
                  <select
                    className="field py-1.5"
                    value={form.department_id || ""}
                    onChange={e => setForm({ ...form, department_id: e.target.value })}
                  >
                    <option value="">Select Department</option>
                    {departments.map(d => (
                      <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Programme</label>
                  <select
                    className="field py-1.5"
                    value={form.programme_id || ""}
                    onChange={e => setForm({ ...form, programme_id: e.target.value, semester_id: "", section_id: "" })}
                  >
                    <option value="">Select Programme</option>
                    {programmes.map(p => (
                      <option key={p.id} value={p.id}>{p.name} ({p.code})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Semester & Year</label>
                  <select
                    className="field py-1.5"
                    value={form.semester_id || ""}
                    onChange={e => setForm({ ...form, semester_id: e.target.value, section_id: "" })}
                  >
                    <option value="">Select Semester</option>
                    {formFilteredSemesters.map(s => (
                      <option key={s.id} value={s.id}>
                        Semester {s.number} (Year {Math.ceil(s.number / 2)})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Enrol in Section</label>
                  <select
                    className="field py-1.5 font-bold text-indigo-700"
                    value={form.section_id || ""}
                    onChange={e => setForm({ ...form, section_id: e.target.value })}
                  >
                    <option value="">Select Section</option>
                    {formFilteredSections.map(sec => (
                      <option key={sec.id} value={sec.id}>
                        {sec.display_name || (sec.section_code ? `${sec.section_code} (Section ${sec.name})` : `Section ${sec.name}`)}
                      </option>
                    ))}
                  </select>
                </div>
              </>
            )}

            {type === "Faculty" && (
              <>
                <div>
                  <label className="block font-semibold mb-1">Department *</label>
                  <select
                    required
                    className="field py-1.5"
                    value={form.department_id || ""}
                    onChange={e => setForm({ ...form, department_id: e.target.value })}
                  >
                    <option value="">Select Department</option>
                    {departments.map(d => (
                      <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Full Name *</label>
                  <input
                    required
                    className="field py-1.5"
                    placeholder="Prof. Alex Smith"
                    value={form.full_name || ""}
                    onChange={e => setForm({ ...form, full_name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Email Address *</label>
                  <input
                    required
                    type="email"
                    className="field py-1.5"
                    placeholder="prof@example.edu"
                    value={form.email || ""}
                    onChange={e => setForm({ ...form, email: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Designation</label>
                  <select
                    className="field py-1.5"
                    value={form.designation || "Assistant Professor"}
                    onChange={e => setForm({ ...form, designation: e.target.value })}
                  >
                    <option value="Professor">Professor</option>
                    <option value="Associate Professor">Associate Professor</option>
                    <option value="Assistant Professor">Assistant Professor</option>
                    <option value="Senior Lecturer">Senior Lecturer</option>
                    <option value="Visiting Faculty">Visiting Faculty</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Highest Qualification</label>
                  <input
                    className="field py-1.5"
                    placeholder="Ph.D. in Computer Science"
                    value={form.highest_qualification || ""}
                    onChange={e => setForm({ ...form, highest_qualification: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Specialisation / Expertise</label>
                  <input
                    className="field py-1.5"
                    placeholder="e.g. Computer Networks, AI/ML, OS"
                    value={form.specialisation || ""}
                    onChange={e => setForm({ ...form, specialisation: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Max Classes Per Day (Safety Limit)</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    className="field py-1.5"
                    value={form.max_classes_per_day || 4}
                    onChange={e => setForm({ ...form, max_classes_per_day: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Max Classes Per Week</label>
                  <input
                    type="number"
                    min="1"
                    max="40"
                    className="field py-1.5"
                    value={form.max_classes_per_week || 18}
                    onChange={e => setForm({ ...form, max_classes_per_week: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Max Consecutive Hours</label>
                  <input
                    type="number"
                    min="1"
                    max="6"
                    className="field py-1.5"
                    value={form.max_consecutive_hours || 2}
                    onChange={e => setForm({ ...form, max_consecutive_hours: e.target.value })}
                  />
                </div>
                <div className="md:col-span-2 flex items-center gap-2 mt-2">
                  <input
                    type="checkbox"
                    id="cross_dept_cb"
                    className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                    checked={Boolean(form.cross_department_approved)}
                    onChange={e => setForm({ ...form, cross_department_approved: e.target.checked })}
                  />
                  <label htmlFor="cross_dept_cb" className="text-xs font-semibold text-slate-700 cursor-pointer">
                    Administrator Approved for Cross-Department Teaching (Exception Permission)
                  </label>
                </div>
              </>
            )}

            {type === "Subjects" && (
              <>
                <div>
                  <label className="block font-semibold mb-1">Department *</label>
                  <select
                    required
                    className="field py-1.5"
                    value={form.department_id || ""}
                    onChange={e => setForm({ ...form, department_id: e.target.value })}
                  >
                    <option value="">Select Department</option>
                    {departments.map(d => (
                      <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Programme</label>
                  <select
                    className="field py-1.5"
                    value={form.programme_id || ""}
                    onChange={e => setForm({ ...form, programme_id: e.target.value })}
                  >
                    <option value="">General (All Programmes)</option>
                    {programmes.map(p => (
                      <option key={p.id} value={p.id}>{p.name} ({p.code})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Semester Number (1-12)</label>
                  <input
                    type="number"
                    min="1"
                    max="12"
                    className="field py-1.5"
                    placeholder="e.g. 1, 2, 3..."
                    value={form.semester_number || ""}
                    onChange={e => setForm({ ...form, semester_number: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Subject Code *</label>
                  <input
                    required
                    className="field py-1.5"
                    placeholder="CS-104"
                    value={form.code || ""}
                    onChange={e => setForm({ ...form, code: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Subject Name *</label>
                  <input
                    required
                    className="field py-1.5"
                    placeholder="Operating Systems"
                    value={form.name || ""}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Session Type *</label>
                  <select
                    className="field py-1.5"
                    value={form.session_type || "LECTURE"}
                    onChange={e => setForm({ ...form, session_type: e.target.value })}
                  >
                    <option value="LECTURE">LECTURE</option>
                    <option value="LABORATORY">LABORATORY</option>
                    <option value="TUTORIAL">TUTORIAL</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Default Duration (mins)</label>
                  <input
                    type="number"
                    className="field py-1.5"
                    value={form.default_duration || 60}
                    onChange={e => setForm({ ...form, default_duration: e.target.value })}
                  />
                </div>
              </>
            )}

            {type === "Faculty Assignments" && (
              <>
                <div>
                  <label className="block font-semibold mb-1">Faculty Member *</label>
                  <select
                    required
                    className="field py-1.5"
                    value={form.faculty_id || ""}
                    onChange={e => setForm({ ...form, faculty_id: e.target.value })}
                  >
                    <option value="">Select Faculty</option>
                    {facultyList.map(f => (
                      <option key={f.id} value={f.id}>{f.full_name} ({f.faculty_id})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Subject *</label>
                  <select
                    required
                    className="field py-1.5"
                    value={form.subject_id || ""}
                    onChange={e => setForm({ ...form, subject_id: e.target.value })}
                  >
                    <option value="">Select Subject</option>
                    {subjects.map(s => (
                      <option key={s.id} value={s.id}>{s.code}: {s.name} ({s.session_type})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Target Section *</label>
                  <select
                    required
                    className="field py-1.5"
                    value={form.section_id || ""}
                    onChange={e => setForm({ ...form, section_id: e.target.value })}
                  >
                    <option value="">Select Section</option>
                    {sections.map(sec => (
                      <option key={sec.id} value={sec.id}>
                        {sec.display_name || (sec.section_code ? `${sec.section_code} (Section ${sec.name})` : `Section ${sec.name}`)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Sessions Per Week *</label>
                  <input
                    required
                    type="number"
                    min="1"
                    max="10"
                    className="field py-1.5"
                    value={form.sessions_per_week || 3}
                    onChange={e => setForm({ ...form, sessions_per_week: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Duration Per Session (mins) *</label>
                  <input
                    required
                    type="number"
                    step="15"
                    className="field py-1.5"
                    value={form.duration_minutes || 60}
                    onChange={e => setForm({ ...form, duration_minutes: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Priority (1-10)</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    className="field py-1.5"
                    value={form.priority || 7}
                    onChange={e => setForm({ ...form, priority: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Required Room Type *</label>
                  <select
                    className="field py-1.5"
                    value={form.required_room_type || "CLASSROOM"}
                    onChange={e => setForm({ ...form, required_room_type: e.target.value })}
                  >
                    <option value="CLASSROOM">CLASSROOM</option>
                    <option value="LABORATORY">LABORATORY</option>
                    <option value="SEMINAR">SEMINAR</option>
                    <option value="AUDITORIUM">AUDITORIUM</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Required Capacity</label>
                  <input
                    type="number"
                    className="field py-1.5"
                    value={form.required_capacity || 40}
                    onChange={e => setForm({ ...form, required_capacity: e.target.value })}
                  />
                </div>
              </>
            )}

            {(type === "Campus" || type === "Classrooms") && (
              <>
                <div>
                  <label className="block font-semibold mb-1">Building</label>
                  <select
                    className="field py-1.5"
                    value={form.building_id || ""}
                    onChange={e => setForm({ ...form, building_id: e.target.value })}
                  >
                    <option value="">Select Building</option>
                    {buildings.map(b => (
                      <option key={b.id} value={b.id}>{b.name} ({b.code})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Floor *</label>
                  <select
                    required
                    className="field py-1.5"
                    value={form.floor_id || ""}
                    onChange={e => setForm({ ...form, floor_id: e.target.value })}
                  >
                    <option value="">Select Floor</option>
                    {floors.map(fl => (
                      <option key={fl.id} value={fl.id}>{fl.name} (Level {fl.level})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Room Name *</label>
                  <input
                    required
                    className="field py-1.5"
                    placeholder="R-201"
                    value={form.name || ""}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1">Room Type *</label>
                  <select
                    className="field py-1.5"
                    value={form.room_type || "CLASSROOM"}
                    onChange={e => setForm({ ...form, room_type: e.target.value })}
                  >
                    <option value="CLASSROOM">CLASSROOM</option>
                    <option value="LABORATORY">LABORATORY</option>
                    <option value="SEMINAR">SEMINAR</option>
                    <option value="AUDITORIUM">AUDITORIUM</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold mb-1">Capacity *</label>
                  <input
                    required
                    type="number"
                    className="field py-1.5"
                    value={form.capacity || 50}
                    onChange={e => setForm({ ...form, capacity: e.target.value })}
                  />
                </div>
              </>
            )}

            <div className="md:col-span-3 flex justify-end gap-2 pt-2 border-t">
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  setEditItem(null);
                  setForm({});
                }}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-all"
              >
                {editItem ? "Update Record" : "Save Record"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* SPECIAL SECTION: CAMPUS GRAPH SIMULATION */}
      {(type === "Campus" || type === "Classrooms") && (
        <div className="panel bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-5 rounded-2xl shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <Network size={20} className="text-indigo-400" />
            <h3 className="font-bold text-base">Campus Graph Simulation (NetworkX & Dijkstra Shortest Path)</h3>
          </div>
          <p className="text-xs text-slate-300">
            Calculates walking distances and shortest paths across university nodes using Dijkstra's algorithm.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div>
              <label className="block text-slate-400 mb-1">Source Classroom</label>
              <select
                className="field bg-slate-800 text-white border-slate-700 py-1.5"
                value={routeRoomA}
                onChange={e => setRouteRoomA(e.target.value)}
              >
                <option value="">Select Room A</option>
                {rooms.map(r => (
                  <option key={r.id} value={r.id}>{r.name} ({r.room_type})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-slate-400 mb-1">Destination Classroom</label>
              <select
                className="field bg-slate-800 text-white border-slate-700 py-1.5"
                value={routeRoomB}
                onChange={e => setRouteRoomB(e.target.value)}
              >
                <option value="">Select Room B</option>
                {rooms.map(r => (
                  <option key={r.id} value={r.id}>{r.name} ({r.room_type})</option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={calculateRoute}
                disabled={routingLoading || !routeRoomA || !routeRoomB}
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white py-2 rounded-lg font-semibold transition-all disabled:opacity-50"
              >
                {routingLoading ? "Calculating..." : "Find Dijkstra Route"}
              </button>
            </div>
          </div>

          {routeResult && (
            <div className="p-3 bg-white/10 rounded-xl backdrop-blur-sm space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-emerald-400">Route Reachable</span>
                <span className="text-slate-300">
                  Total Distance: <strong>{routeResult.distance_meters}m</strong> (~{routeResult.estimated_walking_minutes} mins walking)
                </span>
              </div>
              <div className="flex items-center gap-1.5 flex-wrap text-slate-200">
                {routeResult.path_names?.map((pName: string, i: number) => (
                  <span key={i} className="inline-flex items-center gap-1 bg-slate-800 px-2 py-1 rounded">
                    <span>{pName}</span>
                    {i < routeResult.path_names.length - 1 && <ArrowRight size={11} className="text-indigo-400" />}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* SPECIAL SECTION: EMAIL NOTIFICATIONS CONTROL */}
      {type === "Email Notifications" && (
        <div className="panel bg-indigo-50/70 border border-indigo-100 p-4 rounded-xl space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="font-bold text-sm text-indigo-950 flex items-center gap-2">
                <Mail size={16} className="text-indigo-600" />
                Timetable Email Delivery Engine (SMTP)
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Status: <strong>{smtpStatus?.mode || "MOCK_SIMULATOR"}</strong> • Host: {smtpStatus?.smtp_host}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <select
                className="field text-xs py-1.5"
                value={selectedVersionForEmail}
                onChange={e => setSelectedVersionForEmail(e.target.value)}
              >
                {versions.map(v => (
                  <option key={v.id} value={v.id}>Version {v.version_number} ({v.status})</option>
                ))}
              </select>
              <button
                onClick={dispatchEmails}
                disabled={sendingEmail || !selectedVersionForEmail}
                className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
              >
                <Send size={13} />
                {sendingEmail ? "Dispatching..." : "Send Section PNGs"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Search Input */}
      <div className="relative">
        <Search size={15} className="absolute left-3 top-2.5 text-slate-400" />
        <input
          className="field pl-9 text-xs py-2"
          placeholder={`Search ${type.toLowerCase()}...`}
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {/* Faculty Workload Department Distribution Summary */}
      {type === "Faculty Workload" && workloadData?.department_distribution && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-800">Departmental Workload Distribution & Balance</h3>
            <span className="text-xs text-slate-500 font-semibold">
              Total Faculty: {workloadData.total_faculty} Members
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {workloadData.department_distribution.map((d: any, idx: number) => (
              <div key={idx} className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-sm text-slate-900">{d.department_name}</h4>
                  <span className="badge badge-purple text-[10px]">{d.faculty_count} Faculty</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 pt-1 border-t border-slate-100">
                  <div>
                    <p className="text-slate-400">Weekly Classes</p>
                    <p className="text-base font-bold text-slate-800">{d.total_weekly_classes}</p>
                  </div>
                  <div>
                    <p className="text-slate-400">Teaching Hours</p>
                    <p className="text-base font-bold text-indigo-600">{d.total_weekly_hours}h</p>
                  </div>
                </div>
                <div className="pt-1">
                  <div className="flex justify-between text-[11px] text-slate-500 mb-1">
                    <span>Workload Capacity:</span>
                    <span>{Math.round((d.total_weekly_classes / (d.capacity || 1)) * 100)}%</span>
                  </div>
                  <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-indigo-600 h-full rounded-full"
                      style={{ width: `${Math.min(100, Math.round((d.total_weekly_classes / (d.capacity || 1)) * 100))}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* DATA TABLE */}
      <div className="panel overflow-x-auto p-0 rounded-2xl border border-slate-200">
        <table className="table min-w-full">
          <thead>
            {type === "Departments" && (
              <tr>
                <th>Code</th>
                <th>Department Name</th>
                <th>Description</th>
              </tr>
            )}
            {type === "Programmes" && (
              <tr>
                <th>Code</th>
                <th>Programme Name</th>
                <th>Department</th>
                <th>Duration</th>
                <th>Semesters</th>
                <th>Sections</th>
                <th>Enrolled Students</th>
                <th>Actions</th>
              </tr>
            )}
            {type === "Academic Years" && (
              <tr>
                <th>Year Name</th>
                <th>Start Date</th>
                <th>End Date</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            )}
            {type === "Semesters" && (
              <tr>
                <th>Semester</th>
                <th>Derived Programme Year</th>
                <th>Programme</th>
                <th>Academic Year</th>
                <th>Sections</th>
                <th>Subjects</th>
                <th>Actions</th>
              </tr>
            )}
            {type === "Sections" && (
              <tr>
                <th>Section</th>
                <th>Semester</th>
                <th>Derived Year</th>
                <th>Programme</th>
                <th>Capacity</th>
                <th>Active Enrolments</th>
                <th>Actions</th>
              </tr>
            )}
            {(type === "Students" || type === "Students & Enrolments") && (
              <tr>
                <th>Student ID</th>
                <th>Full Name</th>
                <th>Email</th>
                <th>Programme</th>
                <th>Year / Sem</th>
                <th>Assigned Section</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            )}
            {type === "Faculty" && (
              <tr>
                <th>Faculty ID</th>
                <th>Full Name & Designation</th>
                <th>Department</th>
                <th>Qualification & Specialisation</th>
                <th>Workload Safety Bounds</th>
                <th>Teaching Eligibility</th>
                <th>Cross-Dept</th>
                <th>Actions</th>
              </tr>
            )}
            {type === "Faculty Workload" && (
              <tr>
                <th>Faculty Code & Name</th>
                <th>Department</th>
                <th>Designation & Qualification</th>
                <th>Classes / Day (Mon-Sat)</th>
                <th>Weekly Hours</th>
                <th>Remaining Workload</th>
                <th>Status</th>
              </tr>
            )}
            {type === "Subjects" && (
              <tr>
                <th>Code</th>
                <th>Subject Name</th>
                <th>Programme</th>
                <th>Semester</th>
                <th>Type</th>
                <th>Duration</th>
                <th>Actions</th>
              </tr>
            )}
            {type === "Faculty Assignments" && (
              <tr>
                <th>Faculty</th>
                <th>Subject</th>
                <th>Section</th>
                <th>Weekly Sessions</th>
                <th>Priority</th>
                <th>Room Type</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            )}
            {(type === "Campus" || type === "Classrooms") && (
              <tr>
                <th>Classroom Name</th>
                <th>Type</th>
                <th>Capacity</th>
                <th>Building & Floor</th>
                <th>Status</th>
              </tr>
            )}
            {type === "Email Notifications" && (
              <tr>
                <th>Recipient</th>
                <th>Subject</th>
                <th>Status</th>
                <th>Attempts</th>
                <th>Timestamp</th>
              </tr>
            )}
            {type === "Audit Logs" && (
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>Entity</th>
                <th>Actor</th>
                <th>Details</th>
              </tr>
            )}
          </thead>
          <tbody>
            {filteredItems.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-8 text-slate-400 text-xs">
                  {loading ? "Loading records from database..." : "No records found."}
                </td>
              </tr>
            ) : (
              filteredItems.map((item, idx) => (
                <tr key={item.id || idx}>
                  {type === "Departments" && (
                    <>
                      <td className="font-bold text-indigo-700">{item.code}</td>
                      <td className="font-medium text-slate-900">{item.name}</td>
                      <td className="text-slate-500">{item.description || "—"}</td>
                    </>
                  )}
                  {type === "Programmes" && (
                    <>
                      <td className="font-bold text-indigo-700">{item.code}</td>
                      <td className="font-medium text-slate-900">{item.name}</td>
                      <td>{item.department_name} ({item.department_code})</td>
                      <td>{item.duration_years} Years</td>
                      <td><span className="badge badge-blue">{item.semester_count || 0} Semesters</span></td>
                      <td>{item.section_count || 0}</td>
                      <td>{item.student_count || 0}</td>
                      <td>
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => startEdit(item)}
                            className="text-indigo-600 hover:text-indigo-800 p-1"
                            title="Edit Programme"
                          >
                            <Edit3 size={14} />
                          </button>
                          <button
                            onClick={() => handleDeleteProgramme(item.id, item.name)}
                            className="text-red-500 hover:text-red-700 p-1"
                            title="Safe Delete Programme"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </>
                  )}
                  {type === "Academic Years" && (
                    <>
                      <td className="font-bold text-indigo-700">{item.name}</td>
                      <td>{item.start_date}</td>
                      <td>{item.end_date}</td>
                      <td>
                        <span className={`badge ${item.active ? "badge-green" : "badge-gray"}`}>
                          {item.active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td>
                        {!item.active && (
                          <button
                            onClick={() => handleActivateAcademicYear(item.id, item.name)}
                            className="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-2.5 py-1 rounded font-semibold transition-all"
                          >
                            Set Active
                          </button>
                        )}
                      </td>
                    </>
                  )}
                  {type === "Semesters" && (
                    <>
                      <td className="font-bold text-indigo-700">Semester {item.number}</td>
                      <td>
                        <span className="badge badge-purple font-semibold">
                          Year {item.programme_year || Math.ceil(item.number / 2)}
                        </span>
                      </td>
                      <td className="font-medium">{item.programme_name}</td>
                      <td>{item.academic_year_name}</td>
                      <td>{item.section_count || 0}</td>
                      <td>{item.subject_count || 0}</td>
                      <td>
                        <button
                          onClick={() => handleDeleteSemester(item.id, item.number)}
                          className="text-red-500 hover:text-red-700 p-1"
                          title="Safe Delete Semester"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </>
                  )}
                  {type === "Sections" && (
                    <>
                      <td>
                        <p className="font-bold text-indigo-700">{item.section_code || `Section ${item.name}`}</p>
                        <p className="text-[11px] text-slate-500 font-medium">{item.display_name || `Section ${item.name}`}</p>
                      </td>
                      <td>Semester {item.semester_number}</td>
                      <td><span className="badge badge-purple">Year {item.programme_year}</span></td>
                      <td className="font-medium">{item.programme_name}</td>
                      <td>{item.student_count} Seats</td>
                      <td>
                        <span className="badge badge-green font-bold">
                          {item.active_students || 0} Enrolled
                        </span>
                      </td>
                      <td>
                        <button
                          onClick={() => handleDeleteSection(item.id, item.name)}
                          className="text-red-500 hover:text-red-700 p-1"
                          title="Safe Delete Section"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </>
                  )}
                  {(type === "Students" || type === "Students & Enrolments") && (
                    <>
                      <td className="font-mono text-xs font-bold text-indigo-700">{item.student_id}</td>
                      <td className="font-medium text-slate-900">{item.full_name}</td>
                      <td className="text-slate-500">{item.email}</td>
                      <td>{item.programme_name || "—"}</td>
                      <td>
                        {item.current_semester ? (
                          <span className="badge badge-purple text-[10px]">
                            Year {item.current_year} • Sem {item.current_semester}
                          </span>
                        ) : "—"}
                      </td>
                      <td>
                        <span className={`badge ${item.section_name !== "Unenrolled" ? "badge-green" : "badge-amber"}`} title={item.section_display_name}>
                          {item.section_code || (item.section_name ? `Section ${item.section_name}` : "Unenrolled")}
                        </span>
                        {item.section_display_name && (
                          <span className="text-[10px] text-slate-500 block truncate max-w-[200px]" title={item.section_display_name}>
                            {item.section_display_name}
                          </span>
                        )}
                      </td>
                      <td>
                        <span className={`badge ${item.active ? "badge-green" : "badge-gray"}`}>
                          {item.active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td>
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => {
                              setTransferStudent(item);
                              setTransferTargetSection("");
                            }}
                            className="inline-flex items-center gap-1 text-[11px] bg-slate-100 hover:bg-slate-200 text-slate-700 px-2 py-0.5 rounded font-semibold"
                            title="Transfer Section"
                          >
                            <ArrowLeftRight size={11} />
                            Transfer
                          </button>
                          <button
                            onClick={() => viewStudentAssignment(item)}
                            className="inline-flex items-center gap-1 text-[11px] bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded font-semibold"
                            title="View Academic Assignment"
                          >
                            <FileText size={11} />
                            Profile
                          </button>
                          <button
                            onClick={() => handleDeleteStudent(item.id, item.full_name)}
                            className="text-red-500 hover:text-red-700 p-1"
                            title="Delete Student"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </>
                  )}
                  {type === "Faculty" && (
                    <>
                      <td className="font-bold text-indigo-700">{item.faculty_id}</td>
                      <td>
                        <p className="font-semibold text-slate-900">{item.full_name}</p>
                        <p className="text-[11px] text-slate-500">{item.designation || "Lecturer"}</p>
                      </td>
                      <td>{item.department_name || "—"}</td>
                      <td>
                        <p className="font-medium text-xs text-slate-800">{item.highest_qualification || "Ph.D."}</p>
                        <p className="text-[11px] text-indigo-600 font-semibold">{item.specialisation || "General"}</p>
                      </td>
                      <td className="text-xs">
                        <div className="space-y-0.5">
                          <p><span className="text-slate-400">Max/Day:</span> <strong className="text-slate-700">{item.max_classes_per_day}</strong></p>
                          <p><span className="text-slate-400">Max/Wk:</span> <strong className="text-slate-700">{item.max_classes_per_week}</strong></p>
                          <p><span className="text-slate-400">Max Consec:</span> <strong className="text-slate-700">{item.max_consecutive_hours}h</strong></p>
                        </div>
                      </td>
                      <td>
                        <div className="space-y-1">
                          <div className="flex flex-wrap gap-1 max-w-[200px]">
                            {item.eligible_subjects && item.eligible_subjects.length > 0 ? (
                              item.eligible_subjects.slice(0, 3).map((s: any) => (
                                <span key={s.id} className="inline-block text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                                  {s.code}
                                </span>
                              ))
                            ) : (
                              <span className="text-[11px] text-slate-400">All Dept Subjects</span>
                            )}
                            {item.eligible_subjects && item.eligible_subjects.length > 3 && (
                              <span className="text-[10px] text-slate-500 font-semibold">+{item.eligible_subjects.length - 3} more</span>
                            )}
                          </div>
                          {item.eligible_semesters && item.eligible_semesters.length > 0 && (
                            <p className="text-[10px] text-purple-700 font-semibold">
                              Semesters: {item.eligible_semesters.sort().join(", ")}
                            </p>
                          )}
                        </div>
                      </td>
                      <td>
                        {item.cross_department_approved ? (
                          <span className="badge badge-green text-[10px]">Approved</span>
                        ) : (
                          <span className="badge badge-gray text-[10px]">Standard</span>
                        )}
                      </td>
                      <td>
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => openEligibilityModal(item)}
                            className="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-2 py-1 rounded font-semibold transition-all border border-indigo-200"
                            title="Configure Teaching Eligibility"
                          >
                            Eligibility
                          </button>
                          <button
                            onClick={() => handleResetFacultyPassword(item)}
                            className="text-xs bg-amber-50 hover:bg-amber-100 text-amber-700 px-2 py-1 rounded font-semibold transition-all border border-amber-200 flex items-center gap-1"
                            title="Reset Faculty Password"
                          >
                            <KeyRound size={12} />
                            Reset Pwd
                          </button>
                          <button
                            onClick={() => startEdit(item)}
                            className="text-slate-500 hover:text-indigo-600 p-1 rounded"
                            title="Edit Faculty Details"
                          >
                            <Edit3 size={13} />
                          </button>
                        </div>
                      </td>
                    </>
                  )}
                  {type === "Faculty Workload" && (
                    <>
                      <td>
                        <p className="font-bold text-indigo-700">{item.faculty_code}</p>
                        <p className="font-semibold text-slate-900 text-xs">{item.full_name}</p>
                      </td>
                      <td>{item.department_name}</td>
                      <td>
                        <p className="text-xs font-medium text-slate-800">{item.designation}</p>
                        <p className="text-[11px] text-slate-500">{item.highest_qualification} • {item.specialisation}</p>
                      </td>
                      <td>
                        <div className="flex items-center gap-1 text-[11px]">
                          {["M", "T", "W", "Th", "F", "Sa"].map((dayName, dIdx) => (
                            <span
                              key={dIdx}
                              className={`px-1.5 py-0.5 rounded text-center min-w-[20px] font-bold ${
                                (item.classes_per_day?.[dIdx] || 0) > 0
                                  ? "bg-indigo-100 text-indigo-800 border border-indigo-300"
                                  : "bg-slate-100 text-slate-400"
                              }`}
                              title={`${dayName}: ${item.classes_per_day?.[dIdx] || 0} classes`}
                            >
                              {item.classes_per_day?.[dIdx] || 0}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td>
                        <p className="font-bold text-slate-900 text-xs">{item.weekly_teaching_hours} Hours</p>
                        <p className="text-[10px] text-slate-500">{item.scheduled_classes_per_week || item.assigned_sessions_per_week} Classes / wk</p>
                      </td>
                      <td>
                        <span className="font-bold text-xs text-emerald-700">
                          {item.remaining_available_workload} Classes Available
                        </span>
                        <p className="text-[10px] text-slate-400">Max limit: {item.max_classes_per_week}/wk</p>
                      </td>
                      <td>
                        <span className={`badge ${
                          item.status === "AT_CAPACITY" ? "badge-red" : item.status === "NEAR_LIMIT" ? "badge-yellow" : "badge-green"
                        }`}>
                          {item.status}
                        </span>
                      </td>
                    </>
                  )}
                  {type === "Subjects" && (
                    <>
                      <td className="font-bold text-indigo-700">{item.code}</td>
                      <td className="font-medium text-slate-900">{item.name}</td>
                      <td>{item.programme_name || "General"}</td>
                      <td>
                        {item.semester_number ? (
                          <span className="badge badge-purple text-[10px]">
                            Semester {item.semester_number} (Year {Math.ceil(item.semester_number / 2)})
                          </span>
                        ) : "—"}
                      </td>
                      <td>
                        <span className={`badge ${item.session_type === "LABORATORY" ? "badge-purple" : "badge-blue"}`}>
                          {item.session_type}
                        </span>
                      </td>
                      <td>{item.default_duration} mins</td>
                      <td>
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => startEdit(item)}
                            className="text-indigo-600 hover:text-indigo-800 p-1"
                            title="Edit Subject"
                          >
                            <Edit3 size={14} />
                          </button>
                          <button
                            onClick={() => handleDeleteSubject(item.id, item.name)}
                            className="text-red-500 hover:text-red-700 p-1"
                            title="Safe Delete Subject"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </>
                  )}
                  {type === "Faculty Assignments" && (
                    <>
                      <td className="font-medium">{item.faculty_name} ({item.faculty_code})</td>
                      <td>{item.subject_code}: {item.subject_name}</td>
                      <td>
                        <p className="font-bold text-indigo-700">{item.section_code || `Section ${item.section_name}`}</p>
                        <p className="text-[10px] text-slate-500 font-medium">{item.section_display_name || item.programme_name || ""}</p>
                      </td>
                      <td>{item.sessions_per_week} x {item.duration_minutes}m</td>
                      <td><span className="font-bold text-indigo-600">{item.priority}/10</span></td>
                      <td>{item.required_room_type}</td>
                      <td>
                        <button
                          onClick={() => toggleAssignment(item.id)}
                          className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${
                            item.active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"
                          }`}
                        >
                          {item.active ? "Active" : "Inactive"}
                        </button>
                      </td>
                      <td>
                        <button
                          onClick={() => deleteAssignment(item.id)}
                          className="text-red-500 hover:text-red-700 p-1 rounded"
                          title="Delete Assignment"
                        >
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </>
                  )}
                  {(type === "Campus" || type === "Classrooms") && (
                    <>
                      <td className="font-medium text-slate-900">{item.name}</td>
                      <td>{item.room_type}</td>
                      <td>{item.capacity} Seats</td>
                      <td>{item.building_name || "Main Campus"} • {item.floor_name || "Floor"}</td>
                      <td>
                        <span className={`badge ${item.available ? "badge-green" : "badge-red"}`}>
                          {item.available ? "Available" : "Maintenance"}
                        </span>
                      </td>
                    </>
                  )}
                  {type === "Email Notifications" && (
                    <>
                      <td className="font-medium text-slate-900">{item.recipient_email}</td>
                      <td className="text-slate-600 truncate max-w-xs">{item.subject}</td>
                      <td>
                        <span className={`badge ${item.status === "SENT" ? "badge-green" : "badge-amber"}`}>
                          {item.status}
                        </span>
                      </td>
                      <td>{item.attempts}</td>
                      <td className="text-slate-400 text-[11px]">{item.sent_at || item.created_at}</td>
                    </>
                  )}
                  {type === "Audit Logs" && (
                    <>
                      <td className="text-slate-500 text-[11px] whitespace-nowrap">{item.created_at}</td>
                      <td>
                        <span className={`font-mono text-[11px] px-1.5 py-0.5 rounded ${
                          item.action.startsWith("SQL_TRIGGER")
                            ? "bg-purple-100 text-purple-800 font-bold"
                            : "bg-slate-100 text-slate-800"
                        }`}>
                          {item.action}
                        </span>
                      </td>
                      <td className="font-medium">{item.entity_type}</td>
                      <td className="text-slate-600">{item.actor}</td>
                      <td className="text-slate-500 font-mono text-[10px] truncate max-w-sm">
                        {JSON.stringify(item.details)}
                      </td>
                    </>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* STUDENT SECTION TRANSFER MODAL */}
      {transferStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Transfer Student Section</h3>
                <p className="text-xs text-slate-500">
                  {transferStudent.full_name} ({transferStudent.student_id})
                </p>
              </div>
              <button
                onClick={() => setTransferStudent(null)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={submitStudentTransfer} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold mb-1">Target Section *</label>
                <select
                  required
                  className="field py-2 font-bold text-indigo-700"
                  value={transferTargetSection}
                  onChange={e => setTransferTargetSection(e.target.value)}
                >
                  <option value="">Select Destination Section</option>
                  {sections.map(s => (
                    <option key={s.id} value={s.id}>
                      {s.display_name || (s.section_code ? `${s.section_code} (Section ${s.name})` : `Section ${s.name}`)} ({s.student_count} Students)
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-slate-500 mt-1">
                  The student will be safely moved to this section, existing enrolments deactivated, and student counts updated.
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t">
                <button
                  type="button"
                  onClick={() => setTransferStudent(null)}
                  className="px-3.5 py-1.5 rounded-lg font-semibold text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={transferLoading || !transferTargetSection}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-1.5 rounded-lg font-semibold shadow-sm transition-all disabled:opacity-50"
                >
                  {transferLoading ? "Transferring..." : "Confirm Transfer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* STUDENT COMPLETE ACADEMIC ASSIGNMENT MODAL */}
      {assignmentStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Complete Academic Assignment Profile</h3>
                <p className="text-xs text-slate-500">
                  {assignmentStudent.full_name} • Student ID: <strong>{assignmentStudent.student_id}</strong>
                </p>
              </div>
              <button
                onClick={() => setAssignmentStudent(null)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X size={18} />
              </button>
            </div>

            {assignmentLoading ? (
              <div className="py-8 text-center text-xs text-slate-400">Loading academic assignment...</div>
            ) : assignmentDetails ? (
              <div className="space-y-4 text-xs">
                {/* Academic Hierarchy Summary Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                  <div className="bg-slate-50 border p-2.5 rounded-xl">
                    <span className="text-[10px] text-slate-400 uppercase font-bold">Department</span>
                    <p className="font-bold text-slate-900">{assignmentDetails.department?.name || 'Not Assigned'}</p>
                  </div>
                  <div className="bg-slate-50 border p-2.5 rounded-xl">
                    <span className="text-[10px] text-slate-400 uppercase font-bold">Programme</span>
                    <p className="font-bold text-slate-900">{assignmentDetails.programme?.name || 'Not Assigned'}</p>
                  </div>
                  <div className="bg-slate-50 border p-2.5 rounded-xl">
                    <span className="text-[10px] text-slate-400 uppercase font-bold">Year & Semester</span>
                    <p className="font-bold text-slate-900">
                      Year {assignmentDetails.student?.current_year || '—'} • Sem {assignmentDetails.student?.current_semester || '—'}
                    </p>
                  </div>
                  <div className="bg-indigo-50 border border-indigo-100 p-2.5 rounded-xl">
                    <span className="text-[10px] text-indigo-500 uppercase font-bold">Section</span>
                    <p className="font-bold text-indigo-900" title={assignmentDetails.section?.full_name}>
                      {assignmentDetails.section?.display_name || assignmentDetails.section?.section_code || `Section ${assignmentDetails.section?.name || 'Unenrolled'}`}
                    </p>
                  </div>
                </div>

                {/* Assigned Semester Subjects */}
                <div>
                  <h4 className="font-bold text-slate-800 mb-1.5 flex items-center gap-1.5">
                    <BookOpen size={14} className="text-indigo-600" />
                    Semester Curriculum & Registered Subjects
                  </h4>
                  {assignmentDetails.subjects?.length === 0 ? (
                    <p className="text-slate-400 italic">No curriculum subjects registered for this semester yet.</p>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {assignmentDetails.subjects?.map((sub: any) => (
                        <div key={sub.id} className="border p-2 rounded-lg flex items-center justify-between">
                          <div>
                            <span className="font-bold text-indigo-700">{sub.code}</span>: {sub.name}
                          </div>
                          <span className="badge badge-purple text-[10px]">{sub.session_type}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Section Timetable Sessions */}
                <div>
                  <h4 className="font-bold text-slate-800 mb-1.5 flex items-center gap-1.5">
                    <Calendar size={14} className="text-indigo-600" />
                    Current Section Timetable Classes
                  </h4>
                  {assignmentDetails.timetable_classes?.length === 0 ? (
                    <p className="text-slate-400 italic">No scheduled timetable classes found for this section.</p>
                  ) : (
                    <div className="border rounded-xl overflow-hidden">
                      <table className="table min-w-full text-[11px]">
                        <thead>
                          <tr>
                            <th>Day</th>
                            <th>Time</th>
                            <th>Subject</th>
                            <th>Faculty</th>
                            <th>Classroom</th>
                          </tr>
                        </thead>
                        <tbody>
                          {assignmentDetails.timetable_classes?.map((c: any) => {
                            const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
                            const startH = Math.floor(c.start_minute / 60);
                            const startM = c.start_minute % 60;
                            const endH = Math.floor(c.end_minute / 60);
                            const endM = c.end_minute % 60;
                            return (
                              <tr key={c.id}>
                                <td className="font-bold">{days[c.weekday]}</td>
                                <td>{startH}:{startM === 0 ? '00' : startM} - {endH}:{endM === 0 ? '00' : endM}</td>
                                <td className="font-medium text-slate-900">{c.subject_code}: {c.subject_name}</td>
                                <td>{c.faculty_name}</td>
                                <td><span className="badge badge-blue">{c.room_name}</span></td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            ) : null}

            <div className="flex justify-end pt-2 border-t">
              <button
                type="button"
                onClick={() => setAssignmentStudent(null)}
                className="bg-slate-900 text-white px-4 py-1.5 rounded-lg text-xs font-semibold"
              >
                Close Profile
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Faculty Teaching Eligibility Configuration Modal */}
      {eligibilityFaculty && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-100 max-h-[90vh] overflow-y-auto space-y-5">
            <div className="flex items-center justify-between pb-3 border-b">
              <div>
                <h3 className="font-bold text-lg text-slate-900">Teaching Eligibility Configuration</h3>
                <p className="text-xs text-slate-500">
                  {eligibilityFaculty.full_name} ({eligibilityFaculty.faculty_id}) • {eligibilityFaculty.department_name} • {eligibilityFaculty.designation}
                </p>
              </div>
              <button
                onClick={() => setEligibilityFaculty(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X size={18} />
              </button>
            </div>

            {/* Cross-Department Teaching Approval Exception */}
            <div className="bg-amber-50/80 border border-amber-200 rounded-xl p-3.5 space-y-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="rounded text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                  checked={crossDeptApproved}
                  onChange={e => setCrossDeptApproved(e.target.checked)}
                />
                <span className="font-bold text-xs text-amber-950">
                  Approve Cross-Department Teaching Exception
                </span>
              </label>
              <p className="text-[11px] text-amber-800 ml-6">
                When enabled, administrator explicitly permits this faculty member to teach subjects outside their home department ({eligibilityFaculty.department_name}).
              </p>
            </div>

            {/* Qualified Subjects Selection */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Qualified Subjects ({selectedEligibleSubjects.length} selected)
                </label>
                <div className="flex gap-2 text-[11px]">
                  <button
                    type="button"
                    onClick={() => {
                      const deptSubs = subjects.filter(s => s.department_id === eligibilityFaculty.department_id).map(s => s.id);
                      setSelectedEligibleSubjects(deptSubs);
                    }}
                    className="text-indigo-600 hover:underline font-semibold"
                  >
                    Select All Dept Subjects
                  </button>
                  <span>•</span>
                  <button
                    type="button"
                    onClick={() => setSelectedEligibleSubjects([])}
                    className="text-slate-500 hover:underline"
                  >
                    Clear All
                  </button>
                </div>
              </div>
              <div className="border border-slate-200 rounded-xl p-3 max-h-48 overflow-y-auto grid grid-cols-1 sm:grid-cols-2 gap-2 bg-slate-50/50">
                {subjects.map(s => {
                  const isChecked = selectedEligibleSubjects.includes(s.id);
                  const isSameDept = s.department_id === eligibilityFaculty.department_id;
                  return (
                    <label
                      key={s.id}
                      className={`flex items-start gap-2 p-2 rounded-lg text-xs cursor-pointer border transition-all ${
                        isChecked
                          ? "bg-indigo-50 border-indigo-200 text-indigo-950 font-semibold"
                          : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      <input
                        type="checkbox"
                        className="rounded text-indigo-600 mt-0.5"
                        checked={isChecked}
                        onChange={e => {
                          if (e.target.checked) {
                            setSelectedEligibleSubjects(curr => [...curr, s.id]);
                          } else {
                            setSelectedEligibleSubjects(curr => curr.filter(id => id !== s.id));
                          }
                        }}
                      />
                      <div>
                        <span className="font-bold">{s.code}</span>: {s.name}
                        {!isSameDept && (
                          <span className="ml-1 text-[10px] text-amber-700 bg-amber-100 px-1 py-0.2 rounded font-normal">
                            Cross-Dept
                          </span>
                        )}
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Eligible Semesters Selection */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-slate-800 uppercase tracking-wider">
                Eligible Semesters / Academic Levels ({selectedEligibleSemesters.length} selected)
              </label>
              <p className="text-[11px] text-slate-500">
                Specify academic levels this faculty member is permitted to instruct (e.g. Professors teach all semesters; Assistant Professors restricted to Sem 1-4).
              </p>
              <div className="grid grid-cols-4 sm:grid-cols-8 gap-2">
                {[1, 2, 3, 4, 5, 6, 7, 8].map(semNum => {
                  const isChecked = selectedEligibleSemesters.includes(semNum);
                  return (
                    <button
                      type="button"
                      key={semNum}
                      onClick={() => {
                        if (isChecked) {
                          setSelectedEligibleSemesters(curr => curr.filter(n => n !== semNum));
                        } else {
                          setSelectedEligibleSemesters(curr => [...curr, semNum]);
                        }
                      }}
                      className={`p-2 rounded-xl text-center border text-xs font-bold transition-all ${
                        isChecked
                          ? "bg-purple-600 text-white border-purple-600 shadow-sm"
                          : "bg-white text-slate-700 border-slate-200 hover:bg-slate-100"
                      }`}
                    >
                      Sem {semNum}
                      <span className="block text-[9px] font-normal opacity-80">Year {Math.ceil(semNum / 2)}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t">
              <button
                type="button"
                onClick={() => setEligibilityFaculty(null)}
                className="btn btn-secondary text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={savingEligibility}
                onClick={handleSaveEligibility}
                className="btn btn-primary text-xs"
              >
                {savingEligibility ? "Saving Eligibility..." : "Save Teaching Eligibility"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
