-- ==========================================
-- Migration: conversations alignment
-- Date: 2026-10-30
-- Purpose: add columns introduced in backend/schema.sql that were
--          missing from the live Supabase conversations table.

-- Enum types (guarded)
DO $$ BEGIN
    CREATE TYPE delivery_option AS ENUM ('HOME', 'DESK');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE order_status AS ENUM ('PENDING_CONFIRMATION', 'CONFIRMED', 'REQUIRES_HUMAN', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE conversation_state AS ENUM ('INQUIRY', 'ORDER_INTENT', 'DATA_COLLECTION', 'CONFIRMATION', 'COMPLETED', 'ESCALATION');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Columns
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS merchant_id UUID REFERENCES merchants(id) ON DELETE CASCADE;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS customer_ig_id VARCHAR(255);
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS current_state conversation_state DEFAULT 'INQUIRY';
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS is_bot_active BOOLEAN DEFAULT TRUE;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS collected_fields JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS product_context JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS language VARCHAR(32);
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS attempts INT DEFAULT 0;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS failed_data_attempts INT DEFAULT 0;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS escalated BOOLEAN DEFAULT FALSE;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS open_order_id UUID;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS last_message_at TIMESTAMPTZ DEFAULT NOW();

-- Foreign key: conversations.open_order_id -> orders(order_id)
-- (guarded: only create when the referenced column actually exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'orders'
          AND column_name = 'order_id'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'conversations_open_order_fk'
    ) THEN
        ALTER TABLE public.conversations
            ADD CONSTRAINT conversations_open_order_fk
            FOREIGN KEY (open_order_id) REFERENCES orders(order_id) ON DELETE SET NULL;
    END IF;
END
$$;
