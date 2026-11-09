export interface Exam {
  id: number | string;
  name: string;
  /** yyyy-mm-dd */
  date: string;
}

export interface State {
  exams: Exam[];
  /** Anki's today, yyyy-mm-dd, so the page and the deck screen count alike. */
  today: string;
  added?: number;
  removed?: Exam | null;
}
