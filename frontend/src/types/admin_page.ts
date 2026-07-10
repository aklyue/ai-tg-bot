export interface Source {
  id: number;
  name: string;
  url: string;
  type: string;
  lastParsed: string;
  status: string;
}

export interface Dialogue {
  id: number;
  userId: number;
  userName: string;
  question: string;
  answer: string;
  timestamp: string;
}

export interface KnowledgeItem {
  id: number;
  source: string;
  content: string;
  chunk: string;
}
