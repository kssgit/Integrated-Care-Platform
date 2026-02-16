-- Initial shared PostgreSQL schema layout for service split.

CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS "user";
CREATE SCHEMA IF NOT EXISTS facility;
CREATE SCHEMA IF NOT EXISTS search;
CREATE SCHEMA IF NOT EXISTS integration;

CREATE TABLE IF NOT EXISTS auth.tokens (
    token_id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    access_jti TEXT NOT NULL,
    refresh_jti TEXT NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS auth.login_attempts (
    attempt_id UUID PRIMARY KEY,
    email TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "user".users (
    user_id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL,
    phone_encrypted TEXT,
    phone_hash TEXT,
    profile_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "user".preferences (
    preference_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES "user".users(user_id) ON DELETE CASCADE,
    care_type TEXT NOT NULL,
    location_lat DOUBLE PRECISION,
    location_lng DOUBLE PRECISION,
    search_radius_km INTEGER NOT NULL DEFAULT 5,
    notification_settings JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS facility.facilities (
    facility_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    district_code TEXT NOT NULL,
    address TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    facility_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS facility.facility_sync_log (
    sync_id UUID PRIMARY KEY,
    facility_id TEXT NOT NULL REFERENCES facility.facilities(facility_id),
    source TEXT NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS search.search_documents (
    document_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    district_code TEXT NOT NULL,
    address TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS integration.audit_logs (
    log_id UUID PRIMARY KEY,
    actor_user_id TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    action TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

