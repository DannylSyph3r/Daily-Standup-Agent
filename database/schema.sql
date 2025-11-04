-- ============================================================================
-- Standup Reports Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS standup_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_name VARCHAR(255) NOT NULL,
    report_date DATE NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL,
    
    -- Structured fields (extracted by LLM)
    yesterday_work TEXT,
    today_plan TEXT NOT NULL,
    blockers TEXT,
    additional_notes TEXT,
    
    -- Raw data
    raw_message TEXT NOT NULL,
    
    -- Metadata
    is_within_window BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Prevent duplicate submissions (same name + date)
    UNIQUE(user_name, report_date)
);

-- ============================================================================
-- Daily Summaries Table (Caching Layer)
-- ============================================================================
CREATE TABLE IF NOT EXISTS daily_summaries (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    summary_date DATE NOT NULL UNIQUE,
    full_summary TEXT NOT NULL,
    total_submissions INTEGER NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_reports_date 
    ON standup_reports(report_date);

CREATE INDEX IF NOT EXISTS idx_reports_name_date 
    ON standup_reports(user_name, report_date);

CREATE INDEX IF NOT EXISTS idx_summaries_date 
    ON daily_summaries(summary_date);

-- ============================================================================
-- Cache Invalidation Function
-- ============================================================================
CREATE OR REPLACE FUNCTION invalidate_summary_cache()
RETURNS TRIGGER AS $$
BEGIN
    -- Delete cached summary for the date when new report is inserted
    DELETE FROM daily_summaries WHERE summary_date = NEW.report_date;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Cache Invalidation Trigger
-- ============================================================================
-- Trigger to auto-invalidate cache on new standup submission
DROP TRIGGER IF EXISTS trigger_invalidate_cache ON standup_reports;

CREATE TRIGGER trigger_invalidate_cache
    AFTER INSERT ON standup_reports
    FOR EACH ROW
    EXECUTE FUNCTION invalidate_summary_cache();