export interface ActionItem {
  item: string;
  owner?: string;
  due_date?: string;
}

export interface MeetingNotes {
  summary: string;
  participants: string[];
  decisions: string[];
  action_items: ActionItem[];
}

export interface ModelInfo {
  transcription_model: string;
  llm_model: string;
}

export interface TrimInfo {
  requested: boolean;
  applied: boolean;
  method: string;
  error?: string;
}

export interface MeetingProcessResponse {
  transcript: string;
  notes: MeetingNotes;
  model_info: ModelInfo;
  trim: TrimInfo;
}
