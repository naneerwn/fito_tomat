export type ImageItem = {
  id: number;
  section: number | { id: number; name: string };
  user: number;
  file_path: string;
  file_format: string;
  camera_id?: string | null;
  timestamp: string;
  uploaded_at: string;
};

