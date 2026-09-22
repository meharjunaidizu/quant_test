-- PostgreSQL 15+. All timestamptz values stored in UTC.
CREATE TABLE issuer (
  issuer_id bigserial PRIMARY KEY, legal_name text NOT NULL, cin text,
  sector_code text, industry_code text, is_financial boolean NOT NULL DEFAULT false
);
CREATE TABLE security (
  security_id bigserial PRIMARY KEY, issuer_id bigint NOT NULL REFERENCES issuer,
  isin char(12) NOT NULL, security_type text NOT NULL, first_listed_on date,
  delisted_on date, UNIQUE(isin, security_type)
);
CREATE TABLE listing (
  listing_id bigserial PRIMARY KEY, security_id bigint NOT NULL REFERENCES security,
  exchange text NOT NULL CHECK(exchange IN ('NSE','BSE')), symbol text NOT NULL,
  valid_from date NOT NULL, valid_to date, board text, UNIQUE(exchange,symbol,valid_from)
);
CREATE TABLE classification_history (
  issuer_id bigint REFERENCES issuer, scheme text NOT NULL, sector_code text,
  industry_code text, valid_from date NOT NULL, valid_to date,
  PRIMARY KEY(issuer_id,scheme,valid_from)
);
CREATE TABLE price_daily (
  security_id bigint REFERENCES security, trade_date date, open numeric, high numeric,
  low numeric, close numeric, adjusted_close numeric, volume numeric, traded_value_inr numeric,
  trades bigint, source text NOT NULL, PRIMARY KEY(security_id,trade_date)
);
CREATE TABLE corporate_action (
  action_id bigserial PRIMARY KEY, security_id bigint REFERENCES security,
  action_type text NOT NULL, announced_at timestamptz, ex_date date NOT NULL,
  ratio numeric, cash_amount numeric, source_uri text, revision integer DEFAULT 1
);
CREATE TABLE filing (
  filing_id bigserial PRIMARY KEY, issuer_id bigint REFERENCES issuer,
  filing_type text NOT NULL, period_end date, announced_at timestamptz NOT NULL,
  available_at timestamptz NOT NULL, source_uri text NOT NULL, content_hash text,
  revision integer NOT NULL DEFAULT 1, supersedes_filing_id bigint REFERENCES filing
);
CREATE TABLE financial_fact (
  fact_id bigserial PRIMARY KEY, issuer_id bigint REFERENCES issuer,
  statement_scope text NOT NULL CHECK(statement_scope IN ('CONSOLIDATED','STANDALONE')),
  period_type text NOT NULL CHECK(period_type IN ('QUARTER','YEAR','TTM')),
  period_end date NOT NULL, metric_code text NOT NULL, value numeric, currency char(3), unit_scale numeric,
  available_at timestamptz NOT NULL, filing_id bigint REFERENCES filing, revision integer NOT NULL,
  UNIQUE(issuer_id,statement_scope,period_type,period_end,metric_code,revision)
);
CREATE INDEX financial_fact_pit ON financial_fact(issuer_id,metric_code,available_at DESC);
CREATE TABLE business_kpi_fact (
  issuer_id bigint REFERENCES issuer, kpi_code text, period_end date, value numeric, unit text,
  available_at timestamptz NOT NULL, filing_id bigint REFERENCES filing, revision integer NOT NULL,
  PRIMARY KEY(issuer_id,kpi_code,period_end,revision)
);
CREATE TABLE ownership_fact (
  issuer_id bigint REFERENCES issuer, period_end date, holder_class text, holding_pct numeric,
  shares bigint, available_at timestamptz NOT NULL, filing_id bigint REFERENCES filing,
  revision integer NOT NULL, PRIMARY KEY(issuer_id,period_end,holder_class,revision)
);
CREATE TABLE governance_event (
  event_id bigserial PRIMARY KEY, issuer_id bigint REFERENCES issuer, event_code text NOT NULL,
  severity text NOT NULL, penalty numeric NOT NULL, hard_gate boolean NOT NULL DEFAULT false,
  announced_at timestamptz NOT NULL, effective_from date NOT NULL, effective_to date,
  filing_id bigint REFERENCES filing, source_uri text NOT NULL
);
CREATE TABLE benchmark_price (
  benchmark_code text, trade_date date, adjusted_close numeric NOT NULL,
  PRIMARY KEY(benchmark_code,trade_date)
);
CREATE TABLE feature_snapshot (
  as_of_date date, security_id bigint REFERENCES security, feature_code text,
  raw_value numeric, score numeric, is_available boolean NOT NULL, lineage jsonb,
  config_version text NOT NULL, PRIMARY KEY(as_of_date,security_id,feature_code,config_version)
);
CREATE TABLE score_snapshot (
  as_of_date date, security_id bigint REFERENCES security, raw_mcs numeric,
  adjusted_mcs numeric, coverage numeric, component_scores jsonb, state text,
  velocity_1m numeric, velocity_3m numeric, acceleration numeric,
  eligible boolean, gate_reasons jsonb, config_version text NOT NULL,
  PRIMARY KEY(as_of_date,security_id,config_version)
);
CREATE TABLE forward_label (
  observation_date date, security_id bigint REFERENCES security, horizon_sessions integer,
  target_multiple numeric, hit boolean, first_hit_date date, max_multiple numeric,
  max_drawdown_before_hit numeric, terminal_return numeric, benchmark_excess_return numeric,
  label_version text NOT NULL, PRIMARY KEY(observation_date,security_id,horizon_sessions,target_multiple,label_version)
);

-- Point-in-time selection pattern: latest public revision as of the snapshot cutoff.
-- SELECT DISTINCT ON (issuer_id, metric_code, period_end) * FROM financial_fact
-- WHERE available_at <= :snapshot_cutoff
-- ORDER BY issuer_id, metric_code, period_end, available_at DESC, revision DESC;

