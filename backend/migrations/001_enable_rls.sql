-- Enable Row Level Security on all tables
-- This prevents unauthorized access via Supabase's auto-generated REST API
-- The backend connects as 'postgres' role which bypasses RLS, so no app changes needed

-- ============================================
-- 1. Enable RLS on all tables
-- ============================================
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

-- ============================================
-- 2. Deny all access via Supabase public API (anon/authenticated roles)
--    All data access goes through our backend API only
-- ============================================

-- Users table: no public access
CREATE POLICY "Deny all access for anon on users"
  ON public.users
  FOR ALL
  TO anon
  USING (false);

CREATE POLICY "Deny all access for authenticated on users"
  ON public.users
  FOR ALL
  TO authenticated
  USING (false);

-- Usage table: no public access
CREATE POLICY "Deny all access for anon on usage"
  ON public.usage
  FOR ALL
  TO anon
  USING (false);

CREATE POLICY "Deny all access for authenticated on usage"
  ON public.usage
  FOR ALL
  TO authenticated
  USING (false);

-- Chat sessions table: no public access
CREATE POLICY "Deny all access for anon on chat_sessions"
  ON public.chat_sessions
  FOR ALL
  TO anon
  USING (false);

CREATE POLICY "Deny all access for authenticated on chat_sessions"
  ON public.chat_sessions
  FOR ALL
  TO authenticated
  USING (false);

-- Chat messages table: no public access
CREATE POLICY "Deny all access for anon on chat_messages"
  ON public.chat_messages
  FOR ALL
  TO anon
  USING (false);

CREATE POLICY "Deny all access for authenticated on chat_messages"
  ON public.chat_messages
  FOR ALL
  TO authenticated
  USING (false);

-- ============================================
-- 3. Allow full access for the postgres/service_role (our backend)
--    Note: postgres role bypasses RLS by default, but service_role needs explicit policies
-- ============================================
CREATE POLICY "Service role full access on users"
  ON public.users
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access on usage"
  ON public.usage
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access on chat_sessions"
  ON public.chat_sessions
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access on chat_messages"
  ON public.chat_messages
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
