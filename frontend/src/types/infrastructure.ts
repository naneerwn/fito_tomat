export type Greenhouse = {
  id: number;
  name: string;
  location: string;
};

export type Section = {
  id: number;
  name: string;
  description?: string;
  greenhouse: number;
};

