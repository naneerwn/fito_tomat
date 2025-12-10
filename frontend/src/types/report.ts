export interface Report {
  id: number;
  user: number;
  report_type: string;
  period_start: string;
  period_end: string;
  data: ReportData;
  generated_at: string;
  file_path: string;
}

export interface ReportData {
  period: {
    start: string;
    end: string;
  };
  diagnostics: {
    total: number;
    avg_confidence: number | null;
    distribution: Array<{ disease__name: string; total: number }>;
  };
  recommendations: {
    total: number;
  };
  tasks: {
    total: number;
    completed_on_time: number;
    overdue: number;
  };
  timeseries: Array<{ date: string; total: number }>;
  greenhouse_stats: Array<{ greenhouse: string; section: string; total: number }>;
  operator_stats: Array<{ operator: string; total: number }>;
  economics: {
    prevented_loss: number;
    saved_hours: number;
  };
}

