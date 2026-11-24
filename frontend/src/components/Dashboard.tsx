import { useEffect, useState } from "react";
import {
  Users, GraduationCap, Building2,
  CalendarDays, BookOpen, AlertTriangle,
  UserCheck, CheckCircle2,
  Sparkles, Layers, Cpu
} from "lucide-react";
import {
  ResponsiveContainer,
  XAxis, YAxis, Tooltip, CartesianGrid, AreaChart, Area
} from "recharts";

import api from "../api";

export default function Dashboard() {
  const [stats, setStats] = useState<any>({
    total_students: 0,
    total_faculty: 0,
    total_subjects: 0,
    total_classrooms: 0,
    total_sections: 0,
    active_assignments: 0,
    total_timetables: 0,
    unscheduled_sessions: 0
  });

  const [versions, setVersions] = useState<any[]>([]);
  const [semaphoreStatus, setSemaphoreStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const [statsRes, versionsRes, semRes] = await Promise.all([
          api.get("/academic/stats"),
          api.get("/scheduling/versions"),
          api.get("/os/semaphore/status")
        ]);

        setStats(statsRes.data);
        setVersions(versionsRes.data);
        setSemaphoreStatus(semRes.data);
      } catch {
        setError("Unable to load live dashboard statistics.");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  const cards = [
    { title: "Total Students", value: stats.total_students, icon: GraduationCap, color: "text-blue-600 bg-blue-50" },
    { title: "Total Faculty", value: stats.total_faculty, icon: Users, color: "text-indigo-600 bg-indigo-50" },
    { title: "Total Subjects", value: stats.total_subjects, icon: BookOpen, color: "text-emerald-600 bg-emerald-50" },
    { title: "Classrooms", value: stats.total_classrooms, icon: Building2, color: "text-violet-600 bg-violet-50" },
    { title: "Sections", value: stats.total_sections, icon: Layers, color: "text-amber-600 bg-amber-50" },
    { title: "Active Assignments", value: stats.active_assignments, icon: UserCheck, color: "text-teal-600 bg-teal-50" },
    { title: "Generated Timetables", value: stats.total_timetables, icon: CalendarDays, color: "text-sky-600 bg-sky-50" },
    {
      title: "Unscheduled Sessions",
      value: stats.unscheduled_sessions,
      icon: AlertTriangle,
      color: stats.unscheduled_sessions > 0 ? "text-rose-600 bg-rose-50" : "text-slate-600 bg-slate-50"
    }
  ];

  const chartData = versions.slice(0, 8).map((v: any) => ({
    name: `V${v.version_number}`,
    score: v.quality_score || 100,
    status: v.status
  })).reverse();

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">System Dashboard</h2>
          <p className="text-sm text-slate-500 mt-1">
            Real-time university academic resources, DBMS audit status & OS scheduling engine metrics.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs px-3 py-1.5 rounded-full font-medium">
            <CheckCircle2 size={14} className="text-emerald-600" />
            PostgreSQL ACID Triggers Active
          </div>
          <div className="flex items-center gap-2 bg-indigo-50 border border-indigo-200 text-indigo-800 text-xs px-3 py-1.5 rounded-full font-medium">
            <Cpu size={14} className="text-indigo-600" />
            Semaphore: {semaphoreStatus?.status || "READY"}
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm">
          {error}
        </div>
      )}

      {/* 8 Required Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cards.map(card => {
          const Icon = card.icon;

          return (
            <div key={card.title} className="panel hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    {card.title}
                  </p>
                  <h3 className="text-2xl font-bold mt-2 text-slate-800">
                    {loading ? "..." : card.value}
                  </h3>
                </div>
                <div className={`p-2.5 rounded-xl ${card.color}`}>
                  <Icon size={20} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recharts Graphical Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="panel lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-slate-900">Optimization Quality Scores Across Versions</h3>
              <p className="text-xs text-slate-500">OR-Tools CP-SAT objective satisfaction rate (%)</p>
            </div>
            <Sparkles size={18} className="text-indigo-600" />
          </div>

          <div className="h-64 w-full">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
                  <YAxis domain={[0, 100]} stroke="#94a3b8" fontSize={12} unit="%" />
                  <Tooltip
                    contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0" }}
                  />
                  <Area type="monotone" dataKey="score" stroke="#4f46e5" fillOpacity={1} fill="url(#scoreGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 text-sm">
                No timetable versions generated yet. Go to Scheduling to generate one.
              </div>
            )}
          </div>
        </div>

        <div className="panel space-y-4">
          <h3 className="font-semibold text-slate-900">OS & DBMS Safeguards</h3>
          <div className="space-y-3 text-sm">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <p className="font-semibold text-slate-800">Concurrency Control</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Binary semaphore + PostgreSQL transaction advisory lock (ID: 741852).
              </p>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <p className="font-semibold text-slate-800">Deadlock Prevention</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Strict canonical hierarchy lock ordering eliminating Circular Wait.
              </p>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <p className="font-semibold text-slate-800">Automated SQL Triggers</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Audit logging, session duration checks & manual override flags.
              </p>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <p className="font-semibold text-slate-800">Campus Route Planner</p>
              <p className="text-xs text-slate-500 mt-0.5">
                NetworkX Dijkstra shortest-path walking simulation between rooms.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
