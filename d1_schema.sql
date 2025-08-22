-- Equipment Contacts Database Schema
-- Optimized for fast queries and analytics

-- Main contacts table
CREATE TABLE contacts (
    id TEXT PRIMARY KEY,
    seller_company TEXT,
    primary_phone TEXT,
    primary_location TEXT,
    email TEXT,
    website TEXT,
    total_listings INTEGER DEFAULT 1,
    priority_score INTEGER DEFAULT 0,
    priority_level TEXT DEFAULT 'medium',
    first_contact_date DATE,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    -- Extracted location fields for better queries
    city TEXT,
    state TEXT,
    country TEXT DEFAULT 'USA'
);

-- Equipment categories and sources
CREATE TABLE contact_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT,
    site TEXT,
    category TEXT,
    first_seen DATE,
    listing_count INTEGER DEFAULT 1,
    page_url TEXT,
    FOREIGN KEY (contact_id) REFERENCES contacts (id)
);

-- Equipment details for better analytics
CREATE TABLE equipment_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT,
    equipment_year TEXT,
    equipment_make TEXT,
    equipment_model TEXT,
    listing_price TEXT,
    serial_number TEXT,
    auction_date TEXT,
    listing_url TEXT,
    FOREIGN KEY (contact_id) REFERENCES contacts (id)
);

-- Additional contact info (flexible JSON storage)
CREATE TABLE contact_additional_info (
    contact_id TEXT PRIMARY KEY,
    serial_numbers TEXT, -- JSON array
    auction_dates TEXT,  -- JSON array
    alternate_locations TEXT, -- JSON array
    equipment_years TEXT, -- JSON array
    equipment_makes TEXT, -- JSON array
    equipment_models TEXT, -- JSON array
    listing_prices TEXT, -- JSON array
    listing_urls TEXT, -- JSON array
    FOREIGN KEY (contact_id) REFERENCES contacts (id)
);

-- Indexes for fast queries
CREATE INDEX idx_contacts_phone ON contacts (primary_phone);
CREATE INDEX idx_contacts_company ON contacts (seller_company);
CREATE INDEX idx_contacts_state ON contacts (state);
CREATE INDEX idx_contacts_priority ON contacts (priority_level);
CREATE INDEX idx_contacts_updated ON contacts (last_updated);

CREATE INDEX idx_sources_contact ON contact_sources (contact_id);
CREATE INDEX idx_sources_category ON contact_sources (category);
CREATE INDEX idx_sources_site ON contact_sources (site);

CREATE INDEX idx_equipment_contact ON equipment_data (contact_id);
CREATE INDEX idx_equipment_make ON equipment_data (equipment_make);
CREATE INDEX idx_equipment_year ON equipment_data (equipment_year);

-- View for dashboard queries (combines all data)
CREATE VIEW contact_summary AS
SELECT 
    c.id,
    c.seller_company,
    c.primary_phone,
    c.primary_location,
    c.state,
    c.total_listings,
    c.priority_level,
    c.priority_score,
    c.last_updated,
    GROUP_CONCAT(DISTINCT cs.category) as categories,
    COUNT(DISTINCT cs.category) as category_count,
    COUNT(DISTINCT ed.equipment_make) as unique_makes,
    COUNT(ed.id) as equipment_records
FROM contacts c
LEFT JOIN contact_sources cs ON c.id = cs.contact_id
LEFT JOIN equipment_data ed ON c.id = ed.contact_id
GROUP BY c.id;
