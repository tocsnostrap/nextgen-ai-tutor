-- Initialize TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create additional extensions for better performance
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create read-only user for analytics
CREATE USER analytics_reader WITH PASSWORD 'analytics_password';
GRANT CONNECT ON DATABASE ai_tutor TO analytics_reader;
GRANT USAGE ON SCHEMA public TO analytics_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO analytics_reader;

-- Create backup user
CREATE USER backup_user WITH PASSWORD 'backup_password';
GRANT CONNECT ON DATABASE ai_tutor TO backup_user;
GRANT USAGE ON SCHEMA public TO backup_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_user;

-- Set up monitoring
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET pg_stat_statements.max = 10000;

-- Create indexes for common queries (additional to those in models)
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_user_topic ON learning_sessions(user_id, topic);
CREATE INDEX IF NOT EXISTS idx_interactions_content_search ON session_interactions USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_assessments_score ON assessments(score DESC);
CREATE INDEX IF NOT EXISTS idx_progress_updated ON learning_progress(updated_at DESC);

-- Create materialized views for common analytics queries
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_learning_metrics AS
SELECT 
    DATE(s.start_time) as learning_date,
    s.user_id,
    COUNT(DISTINCT s.id) as session_count,
    SUM(s.duration_seconds) as total_learning_time,
    COUNT(i.id) as interaction_count,
    AVG(CASE WHEN i.correctness THEN 1.0 ELSE 0.0 END) as avg_correctness
FROM learning_sessions s
LEFT JOIN session_interactions i ON s.id = i.session_id
WHERE s.start_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(s.start_time), s.user_id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_metrics ON daily_learning_metrics(learning_date, user_id);

-- Create view for skill mastery trends
CREATE MATERIALIZED VIEW IF NOT EXISTS skill_mastery_trends AS
SELECT 
    p.skill_id,
    p.skill_name,
    p.user_id,
    DATE(p.updated_at) as mastery_date,
    p.mastery_probability,
    p.attempts,
    p.successes
FROM learning_progress p
WHERE p.updated_at >= CURRENT_DATE - INTERVAL '90 days';

CREATE INDEX IF NOT EXISTS idx_skill_trends ON skill_mastery_trends(skill_id, user_id, mastery_date);

-- Refresh materialized views daily
CREATE OR REPLACE FUNCTION refresh_analytics_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_learning_metrics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY skill_mastery_trends;
END;
$$ LANGUAGE plpgsql;

-- Create scheduled job (would be set up with pg_cron in production)
-- SELECT cron.schedule('refresh-analytics-views', '0 2 * * *', 'SELECT refresh_analytics_views()');

-- Set up database parameters for performance
ALTER DATABASE ai_tutor SET work_mem = '16MB';
ALTER DATABASE ai_tutor SET maintenance_work_mem = '256MB';
ALTER DATABASE ai_tutor SET effective_cache_size = '4GB';
ALTER DATABASE ai_tutor SET random_page_cost = 1.1;
ALTER DATABASE ai_tutor SET effective_io_concurrency = 200;

-- Create function for cleaning up old data
CREATE OR REPLACE FUNCTION cleanup_old_data(retention_days INTEGER DEFAULT 365)
RETURNS void AS $$
BEGIN
    -- Archive and delete old sessions
    DELETE FROM learning_sessions 
    WHERE end_time < CURRENT_DATE - retention_days * INTERVAL '1 day'
    AND status = 'completed';
    
    -- Delete old analytics events
    DELETE FROM analytics_events 
    WHERE event_time < CURRENT_DATE - retention_days * INTERVAL '1 day';
    
    -- Vacuum analyze to reclaim space
    VACUUM ANALYZE;
END;
$$ LANGUAGE plpgsql;

-- Create function for getting user learning statistics
CREATE OR REPLACE FUNCTION get_user_learning_stats(user_uuid UUID, days_back INTEGER DEFAULT 30)
RETURNS TABLE(
    total_sessions BIGINT,
    total_learning_time INTERVAL,
    avg_session_duration INTERVAL,
    total_interactions BIGINT,
    avg_correctness DECIMAL,
    skills_learned BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(DISTINCT s.id) as total_sessions,
        SUM(s.duration_seconds * INTERVAL '1 second') as total_learning_time,
        AVG(s.duration_seconds * INTERVAL '1 second') as avg_session_duration,
        COUNT(i.id) as total_interactions,
        AVG(CASE WHEN i.correctness THEN 1.0 ELSE 0.0 END) as avg_correctness,
        COUNT(DISTINCT p.skill_id) FILTER (WHERE p.mastery_probability >= 0.8) as skills_learned
    FROM learning_sessions s
    LEFT JOIN session_interactions i ON s.id = i.session_id
    LEFT JOIN learning_progress p ON s.user_id = p.user_id
    WHERE s.user_id = user_uuid
    AND s.start_time >= CURRENT_DATE - days_back * INTERVAL '1 day';
END;
$$ LANGUAGE plpgsql;

-- Create notification for new high scores
CREATE OR REPLACE FUNCTION notify_high_score()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.score >= 90 THEN
        -- In production, this would send a notification
        -- For now, just log it
        RAISE NOTICE 'User % achieved high score: % on assessment %', 
            NEW.user_id, NEW.score, NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER high_score_notification
AFTER INSERT ON assessments
FOR EACH ROW
EXECUTE FUNCTION notify_high_score();

-- Create view for system health monitoring
CREATE VIEW system_health AS
SELECT 
    'users' as metric,
    COUNT(*) as value,
    MAX(created_at) as last_updated
FROM users
UNION ALL
SELECT 
    'active_sessions',
    COUNT(*),
    MAX(start_time)
FROM learning_sessions 
WHERE status = 'active'
UNION ALL
SELECT 
    'total_interactions_today',
    COUNT(*),
    MAX(timestamp)
FROM session_interactions 
WHERE DATE(timestamp) = CURRENT_DATE
UNION ALL
SELECT 
    'avg_response_time_ms',
    AVG(response_time_ms),
    MAX(timestamp)
FROM session_interactions 
WHERE response_time_ms IS NOT NULL
    AND timestamp >= CURRENT_DATE - INTERVAL '1 day';

-- Grant permissions to analytics user
GRANT SELECT ON daily_learning_metrics TO analytics_reader;
GRANT SELECT ON skill_mastery_trends TO analytics_reader;
GRANT SELECT ON system_health TO analytics_reader;
GRANT EXECUTE ON FUNCTION get_user_learning_stats TO analytics_reader;

-- Log initialization completion
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully';
END $$;