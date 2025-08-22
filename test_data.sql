-- Test data for D1 database
INSERT INTO contacts (id, seller_company, primary_phone, primary_location, city, state, total_listings, priority_level) 
VALUES 
    ('test001', 'ABC Equipment Co', '555-123-4567', 'Dallas, Texas', 'Dallas', 'Texas', 5, 'high'),
    ('test002', 'Heavy Machinery LLC', '555-987-6543', 'Atlanta, Georgia', 'Atlanta', 'Georgia', 12, 'premium'),
    ('test003', 'Construction Plus', '555-555-0123', 'Phoenix, Arizona', 'Phoenix', 'Arizona', 3, 'medium');

INSERT INTO contact_sources (contact_id, site, category, first_seen, listing_count)
VALUES 
    ('test001', 'machinerytrader.com', 'excavators', '2025-08-22', 3),
    ('test001', 'machinerytrader.com', 'backhoes', '2025-08-22', 2),
    ('test002', 'machinerytrader.com', 'cranes', '2025-08-22', 8),
    ('test002', 'machinerytrader.com', 'wheel loaders', '2025-08-22', 4),
    ('test003', 'machinerytrader.com', 'dozers', '2025-08-22', 3);

INSERT INTO equipment_data (contact_id, equipment_make, equipment_year, equipment_model, listing_price)
VALUES 
    ('test001', 'CAT', '2020', '320', '$85000'),
    ('test001', 'John Deere', '2019', '310L', '$75000'),
    ('test002', 'Liebherr', '2021', 'LTM 1090', '$450000'),
    ('test003', 'CAT', '2018', 'D6T', '$125000');
