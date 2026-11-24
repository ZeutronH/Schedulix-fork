import {
  LayoutDashboard, CalendarDays, Clock, Building2,
  FolderTree, Users, GraduationCap, BookOpen,
  UserCheck, ClipboardList, Mail,
  ShieldAlert, LogOut, Calendar, Layers, Grid, DoorClosed, Activity
} from "lucide-react";

interface Props {
  page: string;
  setPage: (page: string) => void;
  logout: () => void;
}

const navigation = [
  { label: "Dashboard", icon: LayoutDashboard },
  { label: "Timetable Generation", icon: Clock },
  { label: "Timetables", icon: CalendarDays },
  { label: "Departments", icon: Building2 },
  { label: "Programmes", icon: FolderTree },
  { label: "Academic Years", icon: Calendar },
  { label: "Semesters", icon: Layers },
  { label: "Sections", icon: Grid },
  { label: "Students & Enrolments", icon: GraduationCap },
  { label: "Faculty", icon: Users },
  { label: "Faculty Workload", icon: Activity },
  { label: "Subjects", icon: BookOpen },
  { label: "Classrooms", icon: DoorClosed },
  { label: "Faculty Assignments", icon: UserCheck },
  { label: "Availability", icon: ClipboardList },
  { label: "Email Notifications", icon: Mail },
  { label: "Audit Logs", icon: ShieldAlert }
];

export default function Sidebar({
  page, setPage, logout
}: Props) {
  return (
    <aside className="w-64 min-h-screen bg-navy text-white p-4 flex flex-col shrink-0 select-none">
      <div className="flex items-center gap-3 px-2 py-4">
        <div className="bg-indigo-600 rounded-xl p-2.5 font-bold shadow-md shadow-indigo-500/30">
          SX
        </div>
        <div>
          <h1 className="font-bold text-lg tracking-tight">Schedulix</h1>
          <p className="text-xs text-slate-400">Timetable & DBMS System</p>
        </div>
      </div>

      <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-3 mt-4 mb-2">
        Academic Workspace
      </div>

      <nav className="space-y-1 flex-1 overflow-y-auto pr-1">
        {navigation.map(item => {
          const Icon = item.icon;
          const isActive = page === item.label;

          return (
            <button
              key={item.label}
              onClick={() => setPage(item.label)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all ${
                isActive
                  ? "bg-indigo-600 text-white font-semibold shadow-sm shadow-indigo-600/30"
                  : "text-slate-300 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <Icon size={17} className={isActive ? "text-white" : "text-slate-400"} />
              <span className="truncate">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="pt-3 border-t border-slate-700/60 mt-2">
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium text-slate-400 hover:text-red-400 hover:bg-slate-800/60 transition-all"
        >
          <LogOut size={17} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
