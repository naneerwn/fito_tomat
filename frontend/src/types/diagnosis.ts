export interface Disease {
  id: number;
  name: string;
  description: string;
  symptoms: string;
}

export interface Image {
  id: number;
  section: number | null;
  user: number;
  file_path: string;
  file_format: string;
  camera_id: string | null;
  timestamp: string;
  uploaded_at: string;
}

export interface Diagnosis {
  id: number;
  image: number;
  disease: number;
  disease_name?: string;
  confidence: number;
  is_verified: boolean;
  verified_by: number | null;
  verified_at: string | null;
  timestamp: string;
  heatmap_path?: string | null;
  heatmap_url?: string | null;
}

export interface Treatment {
  id: number;
  disease: number;
  name: string;
  description: string;
  dosage: string;
  precautions: string;
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

