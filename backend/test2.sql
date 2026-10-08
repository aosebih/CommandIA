-- This MUST fail due to bad phone regex (only 5 digits)
INSERT INTO orders (merchant_id, phone_number) 
VALUES ('11111111-1111-1111-1111-111111111111', '0550123'); 

-- This MUST fail due to Wilaya > 69
INSERT INTO orders (merchant_id, wilaya_code) 
VALUES ('11111111-1111-1111-1111-111111111111', 75);