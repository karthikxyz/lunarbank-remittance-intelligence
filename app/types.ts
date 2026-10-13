export type Processor = {
  name: string;
  transactions: number;
  tpv: number;
  volume_share: number;
  avg_cost: number;
  avg_take_rate: number;
  explicit_fees: number;
  fx_markup: number;
  capital_cost: number;
  avg_delay: number;
};

export type Corridor = {
  corridor: string;
  tpv: number;
  transactions: number;
  avg_cost: number;
  avg_take_rate: number;
  cheapest_processor: string;
  optimization_savings: number;
  routing_savings: number;
  inefficient_processor: string | null;
  inefficient_processors: string[];
  is_inefficient: boolean;
  processors: Processor[];
};

export type Recommendation = {
  corridor: string;
  from: string;
  to: string;
  monthly_savings: number;
  current_take_rate: number;
  target_take_rate: number;
};

export type RateAlert = {
  corridor: string;
  processor: string;
  previous_take_rate: number;
  current_take_rate: number;
  increase_pct: number;
  recent_transactions: number;
};

export type Analytics = {
  generated_at: string;
  period: {
    label: string;
    start: string;
    end: string;
  };
  summary: {
    tpv: number;
    input_transactions: number;
    transactions: number;
    status_counts: Record<"completed" | "failed" | "pending", number>;
    completion_rate: number;
    avg_take_rate: number;
    total_cost: number;
    optimization_savings: number;
    actionable_savings: number;
    inefficient_corridors: number;
    comparison_available: boolean;
    tpv_change_pct: number;
    take_rate_change_bps: number;
  };
  daily_trend: {
    date: string;
    tpv: number;
    transactions: number;
    total_cost: number;
    take_rate: number;
  }[];
  alerts: RateAlert[];
  alerting: {
    threshold_pct: number;
    window_days: number;
    monitored_processor_routes: number;
  };
  corridors: Corridor[];
  recommendations: Recommendation[];
};
