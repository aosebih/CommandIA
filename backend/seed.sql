-- Demo merchant + catalog used by the emulator and the dashboard.
-- Replace meta_page_id with the real Instagram / Page id before going live.

INSERT INTO merchants (id, store_name, meta_page_id, allows_desk_delivery, bot_enabled)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'Brownies Mahelma',
    '123456789_BROWNIES_MAHELMA_ID',
    TRUE,
    TRUE
)
ON CONFLICT (meta_page_id) DO NOTHING;

INSERT INTO products (id, merchant_id, name, price_da, stock_quantity)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    'Brownie Classique',
    1550.00,
    40
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO shipping_rates (merchant_id, wilaya_code, home_fee_da, desk_fee_da)
VALUES
    ('11111111-1111-1111-1111-111111111111', 16, 600.00, 400.00),
    ('11111111-1111-1111-1111-111111111111', 31, 800.00, 500.00),
    ('11111111-1111-1111-1111-111111111111', 9, 700.00, 450.00)
ON CONFLICT (merchant_id, wilaya_code) DO NOTHING;
