export interface Admin {
  id: string;
  username: string;
  email: string;
  role: string;
}

export interface Department {
  id: string;
  name: string;
  code: string;
  description?: string;
}

export interface Programme {
  id: string;
  department_id: string;
  department_name?: string;
  department_code?: string;
  name: string;
  code: string;
  duration_years: number;
  semester_count?: number;
  section_count?: number;
  student_count?: number;
  subject_count?: number;
}

export interface AcademicYear {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  active: boolean;
}

export interface Semester {
  id: string;
  programme_id: string;
  programme_name?: string;
  academic_year_id: string;
  academic_year_name?: string;
  number: number;
  programme_year?: number;
  section_count?: number;
  subject_count?: number;
}

export interface Section {
  id: string;
  name: string;
  section_code?: string;
  display_name?: string;
  full_name?: string;
  student_count: number;
  programme_id: string;
  programme_name?: string;
  programme_code?: string;
  semester_id: string;
  semester_number?: number;
  programme_year?: number;
  active_students?: number;
}

export interface Faculty {
  id: string;
  faculty_id: string;
  full_name: string;
  email: string;
  phone?: string;
  department_id: string;
  designation?: string;
  active: boolean;
}

export interface Student {
  id: string;
  student_id: string;
  full_name: string;
  email: string;
  phone?: string;
  admission_year: number;
  active: boolean;
  department_id?: string;
  department_name?: string;
  programme_id?: string;
  programme_name?: string;
  current_year?: number;
  current_semester?: number;
  section_id?: string;
  section_name?: string;
  section_code?: string;
  section_display_name?: string;
  enrolment_id?: string;
}

export interface Subject {
  id: string;
  department_id: string;
  department_name?: string;
  department_code?: string;
  programme_id?: string;
  programme_name?: string;
  semester_number?: number;
  semester_id?: string;
  code: string;
  name: string;
  session_type: string;
  default_duration: number;
}

export interface FacultyAssignment {
  id: string;
  faculty_id: string;
  faculty_name?: string;
  faculty_code?: string;
  subject_id: string;
  subject_name?: string;
  subject_code?: string;
  section_id: string;
  section_name?: string;
  section_code?: string;
  section_display_name?: string;
  programme_name?: string;
  department_name?: string;
  semester_number?: number;
  sessions_per_week: number;
  duration_minutes: number;
  priority: number;
  required_capacity: number;
  required_room_type: string;
  active: boolean;
}

export interface Room {
  id: string;
  code?: string;
  name: string;
  floor_id: string;
  floor_name?: string;
  building_name?: string;
  room_type: string;
  capacity: number;
  available: boolean;
  equipment?: string[];
}

export interface Building {
  id: string;
  name: string;
  code: string;
  available: boolean;
}

export interface Floor {
  id: string;
  building_id: string;
  name: string;
  level: number;
}

export interface TimetableEntry {
  id: string;
  assignment_id?: string;
  subject: string;
  subject_code?: string;
  faculty: string;
  faculty_code?: string;
  faculty_id?: string;
  section?: string;
  section_id?: string;
  programme?: string;
  department?: string;
  semester?: number;
  academic_year?: string;
  room: string;
  room_id?: string;
  building?: string;
  floor?: string;
  weekday: number;
  start: string;
  end: string;
  start_minute: number;
  end_minute: number;
  duration?: number;
  session_type: string;
  session_number?: number;
  manual_override?: boolean;
}

export interface TimetableVersion {
  id: string;
  version_number: number;
  status: string;
  algorithm: string;
  priority_weight: number;
  sjf_weight: number;
  quality_score: number;
  statistics: Record<string, unknown>;
  section_id?: string;
  section_name?: string;
  section_display_name?: string;
  semester_id?: string;
  programme_id?: string;
  academic_year_id?: string;
  created_at?: string;
  published_at?: string;
}

export interface AuditLogItem {
  id: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  actor: string;
  details: Record<string, any>;
  created_at: string;
}

export interface EmailNotificationItem {
  id: string;
  version_id: string;
  recipient_type: string;
  recipient_id: string;
  recipient_email: string;
  subject: string;
  status: string;
  attempts: number;
  last_error?: string;
  created_at?: string;
  sent_at?: string;
}
