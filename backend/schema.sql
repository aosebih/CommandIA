-- ==========================================
-- 1. CUSTOM ENUM TYPES
-- ==========================================
CREATE TYPE delivery_option AS ENUM ('HOME', 'DESK');
CREATE TYPE order_status AS ENUM ('PENDING_CONFIRMATION', 'CONFIRMED', 'REQUIRES_HUMAN', 'CANCELLED');
CREATE TYPE conversation_state AS ENUM ('INQUIRY', 'ORDER_INTENT', 'DATA_COLLECTION', 'CONFIRMATION', 'COMPLETED', 'ESCALATED');

-- ==========================================
-- 2. MERCHANTS TABLE
-- ==========================================
CREATE TABLE merchants (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    store_name VARCHAR(255) NOT NULL,
    meta_page_id VARCHAR(255) UNIQUE NOT NULL,
    meta_access_token TEXT,
    allows_desk_delivery BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- 3. PRODUCTS CATALOG TABLE
-- ==========================================
CREATE TABLE products (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    merchant_id UUID REFERENCES merchants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    price_da NUMERIC(10, 2) NOT NULL,
    stock_quantity INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- 4. CONVERSATIONS TABLE
-- ==========================================
CREATE TABLE conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    merchant_id UUID REFERENCES merchants(id) ON DELETE CASCADE,
    customer_ig_id VARCHAR(255) NOT NULL,
    current_state conversation_state DEFAULT 'INQUIRY',
    is_bot_active BOOLEAN DEFAULT TRUE,
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(merchant_id, customer_ig_id)
);

-- ==========================================
-- 5. MESSAGES TABLE (Chat Memory)
-- ==========================================
CREATE TABLE messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type VARCHAR(20) CHECK (sender_type IN ('CUSTOMER', 'BOT', 'HUMAN')),
    message_text TEXT NOT NULL,
    raw_payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- 6. SHIPPING RATES TABLE
-- ==========================================
CREATE TABLE shipping_rates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    merchant_id UUID REFERENCES merchants(id) ON DELETE CASCADE,
    wilaya_code INT CHECK (wilaya_code >= 1 AND wilaya_code <= 69),
    home_fee_da NUMERIC(10, 2) NOT NULL DEFAULT 600.00,
    desk_fee_da NUMERIC(10, 2) NOT NULL DEFAULT 400.00,
    UNIQUE(merchant_id, wilaya_code)
);

-- ==========================================
-- 7. ORDERS TABLE
-- ==========================================
CREATE TABLE orders (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    merchant_id UUID REFERENCES merchants(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    
    -- The 5 Sacred Fields
    customer_name VARCHAR(255),
    phone_number VARCHAR(10) CHECK (phone_number IS NULL OR phone_number ~ '^0[567][0-9]{8}$'), 
    wilaya_code INT CHECK (wilaya_code IS NULL OR (wilaya_code >= 1 AND wilaya_code <= 69)),
    wilaya_name VARCHAR(100),
    delivery_type delivery_option,
    address TEXT,
    
    -- COD Pricing Totals
    subtotal_da NUMERIC(10, 2) DEFAULT 0.00,
    shipping_fee_da NUMERIC(10, 2) DEFAULT 0.00,
    total_price_da NUMERIC(10, 2) DEFAULT 0.00,
    
    status order_status DEFAULT 'PENDING_CONFIRMATION',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- 8. ORDER ITEMS TABLE (Multiple Items)
-- ==========================================
CREATE TABLE order_items (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    extracted_product_name VARCHAR(255) NOT NULL,
    quantity INT DEFAULT 1 CHECK (quantity > 0),
    unit_price_da NUMERIC(10, 2),
    attributes JSONB, 
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==========================================
-- 9. AUTOMATIC UPDATED_AT TRIGGER
-- ==========================================
CREATE OR REPLACE FUNCTION update_modified_column()   
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;   
END;
$$ language 'plpgsql';

CREATE TRIGGER update_orders_modtime 
BEFORE UPDATE ON orders 
FOR EACH ROW EXECUTE PROCEDURE update_modified_column();
