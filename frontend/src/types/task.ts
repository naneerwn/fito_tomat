export interface Task {
  id: number;
  recommendation: number;
  operator: number;
  description: string;
  status: string;
  deadline: string;
  created_at: string;
  completed_at: string | null;
  treatment_plan?: string; // План лечения из рекомендации
}

export interface Recommendation {
  id: number;
  diagnosis: number;
  agronomist: number;
  treatment_plan_text: string;
  status: string;
  created_at: string;
  updated_at: string;
}

