export interface DashboardSummary {
  revenue_total: number;
  cost_total: number;
  profit_total: number;
  roi_pct: number;
  period: string;
  is_mock: boolean;
  transaction_count: number;
  avg_profit_per_card: number;
}

export interface TrajectoryPoint {
  date: string;
  revenue: number;
  cost: number;
  profit: number;
  cumulative_profit: number;
}

export interface TrajectoryResponse {
  data: TrajectoryPoint[];
  period: string;
  is_mock: boolean;
}

export interface Transaction {
  id: number;
  ebay_item_id?: string;
  transaction_type: "purchase" | "sale";
  card_name: string;
  player_name?: string;
  year?: number;
  variation?: string;
  grade?: string;
  amount: number;
  ebay_fees: number;
  shipping_cost: number;
  net_amount?: number;
  transaction_date: string;
  source: string;
  reconciled: boolean;
  notes?: string;
  created_at: string;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  limit: number;
}

export interface ResearchResult {
  title: string;
  price: number;
  sale_date?: string;
  image_url?: string;
  listing_url?: string;
  grade?: string;
}

export interface ResearchResponse {
  results: ResearchResult[];
  query: string;
  scraped_at: string;
  total_found: number;
  avg_price?: number;
  price_range?: { min: number; max: number };
  ai_analysis_enabled: boolean;
}

export interface Prospect {
  id: number;
  name: string;
  position?: string;
  team?: string;
  rank_current?: number;
  rank_previous?: number;
  rank_change: number;
  eta?: string;
  scouting_grade?: string;
  is_rising: boolean;
  last_updated?: string;
  source: string;
}

export interface ProspectsResponse {
  prospects: Prospect[];
  last_updated?: string;
  total: number;
}

export interface CardOut {
  id: number;
  card_name: string;
  player_name?: string;
  year?: number;
  variation?: string;
  grade?: string;
  is_owned: boolean;
  is_watchlist: boolean;
  purchase_price?: number;
}

export interface PriceHistoryOut {
  id: number;
  card_id: number;
  snapshot_date: string;
  avg_sale_price?: number;
  min_price?: number;
  max_price?: number;
  sample_count: number;
}

export interface WatchlistEntry {
  card: CardOut;
  latest_price?: number;
  price_change_pct?: number;
  suggested_list_price?: number;
  price_history: PriceHistoryOut[];
}

export interface StatementLine {
  id: number;
  upload_id: number;
  line_date?: string;
  description?: string;
  amount?: number;
  category: string;
  reconciled: boolean;
  transaction_id?: number;
}

export interface StatementUpload {
  id: number;
  filename: string;
  file_type: string;
  bank_name: string;
  upload_date: string;
  lines_parsed: number;
  lines_reconciled: number;
}

export interface UploadResponse {
  upload_id: number;
  lines_found: number;
  preview: StatementLine[];
  message: string;
}
