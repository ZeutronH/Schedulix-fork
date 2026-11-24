
import { useState, useEffect } from "react";
import api from "../api";
import type { Section } from "../types";

const WEEKDAYS = [
  "Monday", "Tuesday", "Wednesday",
  "Thursday", "Friday", "Saturday", "Sunday"
];

export default function Scheduling() {
  const [mode, setMode] = useState("HYBRID");
  const [priority, setPriority] = useState(65);
  const [days, setDays] = useState([0, 1, 2, 3, 4, 5]);
  const [start, setStart] = useState("08:00:00");
  const [end, setEnd] = useState("18:00:00");
  const [sections, setSections] = useState<Section[]>([]);
  const [selectedSection, setSelectedSection] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/academic/sections").then(res => setSections(res.data || [])).catch(() => {});
  }, []);

  function toggleDay(day: number) {
    setDays(current =>
      current.includes(day)
        ? current.filter(value => value !== day)
        : [...current, day].sort()
    );
  }

  async function generate() {
    setLoading(true);
    setError("");
    setResult(null);

    if (!days.length) {
      setError("Select at least one working day.");
      setLoading(false);
      return;
    }

    try {
      const response = await api.post("/scheduling/generate", {
        mode,
        section_id: selectedSection || undefined,
        priority_weight: mode === "HYBRID" ? priority / 100 : 0.65,
        sjf_weight: mode === "HYBRID" ? (100 - priority) / 100 : 0.35,
        weekdays: days,
        day_start: start,
        day_end: end,
        time_limit_seconds: 60
      });

      setResult(response.data);

      if (!response.data.version_id) {
        const reasons = (response.data.unscheduled || []).map((u: any) => `${u.subject || u.assignment_id || 'Class'}: ${u.reason}`).filter(Boolean);
        setError(
          response.data.message ||
          (reasons.length > 0 ? `Solver status: ${response.data.status}. ${reasons.join(' | ')}` : "The solver could not create a timetable. Review the diagnostics below.")
        );
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : JSON.stringify(detail || "Timetable generation failed.")
      );
    } finally {
      setLoading(false);
    }
  }

  async function approve() {
    if (!result?.version_id) return;
    try {
      await api.post(
        `/scheduling/versions/${result.version_id}/approve`,
        { comments: "Approved through admin dashboard" }
      );
      setResult((current: any) => ({ ...current, status: "APPROVED" }));
    } catch (err: any) {
      setError(
        err.response?.data?.detail
          ? JSON.stringify(err.response.data.detail)
          : "Approval failed."
      );
    }
  }

  async function publish() {
    if (!result?.version_id) return;
    try {
      const response = await api.post(
        `/scheduling/versions/${result.version_id}/publish`
      );
      setResult((current: any) => ({
        ...current,
        status: response.data.status
      }));
    } catch (err: any) {
      setError(
        err.response?.data?.detail
          ? JSON.stringify(err.response.data.detail)
          : "Publishing failed."
      );
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Timetable Scheduler</h2>
        <p className="text-sm text-slate-500 mt-1">
          Constraint-based scheduling using OR-Tools CP-SAT
        </p>
      </div>

      <div className="panel space-y-5">
        <div>
          <label className="block text-sm font-semibold mb-2">
            Scheduling algorithm
          </label>
          <select
            className="field"
            value={mode}
            onChange={e => setMode(e.target.value)}
          >
            <option value="HYBRID">Hybrid Priority–SJF</option>
            <option value="PRIORITY">Priority Scheduling</option>
            <option value="SJF">Shortest Job First</option>
          </select>
        </div>

        {mode === "HYBRID" && (
          <div>
            <label className="block text-sm font-semibold">
              Priority weight: {priority}%
            </label>
            <input
              className="w-full mt-2"
              type="range"
              min="0"
              max="100"
              value={priority}
              onChange={e => setPriority(Number(e.target.value))}
            />
            <div className="text-sm text-slate-500">
              SJF weight: {100 - priority}%
            </div>
          </div>
        )}

        <div>
          <label className="block text-sm font-semibold mb-2">
            Working days
          </label>
          <div className="flex flex-wrap gap-2">
            {WEEKDAYS.map((day, index) => (
              <button
                type="button"
                key={day}
                onClick={() => toggleDay(index)}
                className={`px-3 py-2 rounded-lg border text-sm ${
                  days.includes(index)
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "bg-white text-slate-700 border-slate-300"
                }`}
              >
                {day}
              </button>
            ))}
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-semibold mb-2">
              Day starts
            </label>
            <input
              className="field"
              type="time"
              value={start.slice(0, 5)}
              onChange={e => setStart(`${e.target.value}:00`)}
            />
          </div>
          <div>
            <label className="block text-sm font-semibold mb-2">
              Day ends
            </label>
            <input
              className="field"
              type="time"
              value={end.slice(0, 5)}
              onChange={e => setEnd(`${e.target.value}:00`)}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-semibold mb-2">
            Target Academic Section (Optional)
          </label>
          <select
            className="field"
            value={selectedSection}
            onChange={e => setSelectedSection(e.target.value)}
          >
            <option value="">All Academic Sections (University-wide)</option>
            {sections.map(s => (
              <option key={s.id} value={s.id}>
                {s.display_name || (s.section_code ? `${s.section_code} (Section ${s.name})` : `Section ${s.name}`)}
              </option>
            ))}
          </select>
          <p className="text-xs text-slate-500 mt-1">
            Choose a specific section to generate its schedule independently, or leave unselected to generate across all active sections.
          </p>
        </div>

        <div className="rounded-lg bg-indigo-50 text-indigo-900 p-4 text-sm">
          <strong>Scheduling constraints</strong>
          <p className="mt-1">
            The solver checks faculty availability, room type and capacity,
            room availability, section clashes and campus resource blocks.
          </p>
        </div>

        <button
          className="primary"
          disabled={loading}
          onClick={generate}
        >
          {loading ? "Optimising timetable..." : "Generate timetable"}
        </button>

        {error && (
          <pre className="whitespace-pre-wrap text-sm text-red-700 bg-red-50 p-3 rounded-lg">
            {error}
          </pre>
        )}
      </div>

      {result && (
        <div className="panel space-y-4">
          <h3 className="font-bold text-lg">Optimisation result</h3>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Metric label="Solver" value={result.solver || result.status || "—"} />
            <Metric
              label="Quality"
              value={`${result.quality_score ?? 0}%`}
            />
            <Metric
              label="Scheduled"
              value={result.statistics?.scheduled ?? 0}
            />
            <Metric
              label="Unscheduled"
              value={result.unscheduled?.length ?? 0}
            />
          </div>

          {result.version_id && (
            <>
              <p className="text-sm">
                Version: {result.version_number}
              </p>
              <p className="text-sm">
                Validation:{" "}
                <strong>
                  {result.validation?.valid ? "Passed" : "Failed"}
                </strong>
              </p>
            </>
          )}

          {result.unscheduled?.length > 0 && (
            <div className="bg-red-50 rounded-lg p-4">
              <h4 className="font-semibold text-red-800">
                Unscheduled sessions
              </h4>
              {result.unscheduled.map((item: any, index: number) => (
                <p className="text-sm mt-2" key={index}>
                  {item.subject || item.assignment_id || "Assignment"}:
                  {" "}{item.reason}
                </p>
              ))}
            </div>
          )}

          {result.version_id && result.status === "DRAFT" && (
            <button className="primary" onClick={approve}>
              Approve timetable
            </button>
          )}

          {result.status === "APPROVED" && (
            <button className="primary" onClick={publish}>
              Publish timetable
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="bg-slate-50 p-3 rounded-lg">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="font-bold text-xl mt-1">{value}</p>
    </div>
  );
}
