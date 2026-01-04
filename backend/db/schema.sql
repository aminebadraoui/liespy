-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Users table (linked to Supabase Auth or device ID)
create table public.users (
  id uuid primary key default uuid_generate_v4(),
  anonymous_id text unique, -- For device-based auth if needed
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Subscriptions table
create table public.subscriptions (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references public.users(id) not null,
  status text not null, -- 'active', 'expired', 'grace_period'
  tier text not null default 'free', -- 'free', 'premium'
  original_transaction_id text, -- Apple StoreKit transaction ID
  expires_at timestamp with time zone,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Scans table (history of user scans)
create table public.scans (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references public.users(id) not null,
  scan_type text not null check (scan_type in ('page', 'text')),
  risk_level text check (risk_level in ('low', 'medium', 'high')),
  url text,
  page_title text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Claims table (individual findings within a scan)
create table public.claims (
  id uuid primary key default uuid_generate_v4(),
  scan_id uuid references public.scans(id) on delete cascade not null,
  claim_text text not null,
  category text not null, -- 'health', 'financial', 'urgency', etc.
  risk_level text not null, -- 'low', 'medium', 'high'
  explanation text,
  confidence float,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Feedback table (user feedback on specific claims)
create table public.feedback (
  id uuid primary key default uuid_generate_v4(),
  claim_id uuid references public.claims(id) on delete cascade not null,
  user_id uuid references public.users(id) not null,
  helpful boolean,
  report_reason text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS Policies (Row Level Security) - Basic setup
alter table public.users enable row level security;
alter table public.subscriptions enable row level security;
alter table public.scans enable row level security;
alter table public.claims enable row level security;
alter table public.feedback enable row level security;

-- Policy: Users can only see their own data
-- Note: complex auth mapping might be needed depending on how anonymous_id is handled vs Supabase Auth.
-- For now, assuming standard Supabase Auth for simplicity or server-side handling.
