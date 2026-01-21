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

export interface TranscriptSegment {
  speaker: string;
  text: string;
  start_time?: number;
  end_time?: number;
}

export interface TranscribeResponse {
  transcript_text: string;
  segments: TranscriptSegment[];
  transcription_model: string;
  trim: TrimInfo;
}

export interface SummarizeRequest {
  transcript: string;
  language?: string;
}

export interface SummarizeResponse {
  notes: MeetingNotes;
  llm_model: string;
}

export interface MeetingProcessResponse {
  transcript: string;
  notes: MeetingNotes;
  model_info: ModelInfo;
  trim: TrimInfo;
}

export interface HistoryMetadata {
  transcriptionModel: string;
  llmModel: string | null;
  speakerCount: number;
  wordCount: number;
}

export interface HistoryEntry {
  fileHash: string;
  fileName: string;
  fileSize: number;
  duration: number;
  processedAt: number;
  transcript: TranscribeResponse;
  summary: SummarizeResponse | null;
  metadata: HistoryMetadata;
}
