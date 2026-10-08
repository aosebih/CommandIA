-- TEST 1: Insert a test merchant
INSERT INTO merchants (id, store_name, meta_page_id) 
VALUES ('11111111-1111-1111-1111-111111111111', 'DZ Fashion Store', 'PAGE_123456');

-- TEST 2: Valid Order Insertion (Should PASS)
INSERT INTO orders (id, merchant_id, customer_name, phone_number, wilaya_code, wilaya_name, delivery_type, subtotal_da, shipping_fee_da, total_price_da, status)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    'Fadoua Cheriet',
    '0550123456',
    16,
    'Alger',
    'HOME',
    4500.00,
    600.00,
    5100.00,
    'CONFIRMED'
);

-- TEST 3: Insert Multi-Item Products (Should PASS)
INSERT INTO order_items (order_id, extracted_product_name, quantity, unit_price_da, attributes)
VALUES 
('22222222-2222-2222-2222-222222222222', 'Robe d-été', 1, 2500.00, '{"size": "M", "color": "Noir"}'),
('22222222-2222-2222-2222-222222222222', 'Sac à main', 1, 2000.00, '{"color": "Marron"}');

-- Check inserted data
SELECT 
    o.id AS order_id, 
    o.customer_name, 
    o.phone_number, 
    o.wilaya_name, 
    o.total_price_da,
    i.extracted_product_name,
    i.quantity,
    i.attributes
FROM orders o
JOIN order_items i ON o.id = i.order_id;
