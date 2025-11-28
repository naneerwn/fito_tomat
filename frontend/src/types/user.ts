export type AuthUser = {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: number | null;
  role_name?: string | null;
  is_active: boolean;
};

