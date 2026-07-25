PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ships (
    ship_id TEXT PRIMARY KEY,
    ship_name_ko TEXT NOT NULL,
    ship_name_en TEXT,
    asset_category TEXT NOT NULL,
    is_archaeological_shipwreck INTEGER NOT NULL,
    period TEXT,
    year_ce INTEGER,
    site_location TEXT,
    site_depth_m TEXT,
    research_summary TEXT
);

CREATE TABLE IF NOT EXISTS models (
    model_id TEXT PRIMARY KEY,
    ship_id TEXT NOT NULL,
    variant TEXT NOT NULL,
    generation_method TEXT,
    generation_tool TEXT,
    target_measurement_type TEXT,
    target_length_m REAL,
    target_width_m REAL,
    target_height_m REAL,
    bbox_x_units REAL,
    bbox_y_units REAL,
    bbox_z_units REAL,
    bbox_longest_units REAL,
    bbox_middle_units REAL,
    bbox_shortest_units REAL,
    recommended_uniform_scale REAL,
    scaled_length_m REAL,
    scaled_width_m REAL,
    scaled_height_m REAL,
    vertex_count INTEGER,
    triangle_count INTEGER,
    mesh_count INTEGER,
    primitive_count INTEGER,
    material_count INTEGER,
    texture_count INTEGER,
    orientation_reviewed INTEGER NOT NULL DEFAULT 0,
    scale_reviewed INTEGER NOT NULL DEFAULT 0,
    mesh_cleaned INTEGER NOT NULL DEFAULT 0,
    collision_ready INTEGER NOT NULL DEFAULT 0,
    scan_status TEXT,
    notes TEXT,
    FOREIGN KEY (ship_id) REFERENCES ships(ship_id)
);

CREATE TABLE IF NOT EXISTS files (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL,
    file_role TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    extension TEXT,
    exists_on_disk INTEGER NOT NULL,
    size_bytes INTEGER,
    size_mib REAL,
    sha256 TEXT,
    UNIQUE(model_id, file_role),
    FOREIGN KEY (model_id) REFERENCES models(model_id)
);

CREATE TABLE IF NOT EXISTS sources (
    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL,
    source_role TEXT NOT NULL,
    url TEXT NOT NULL,
    organization TEXT,
    license_note TEXT,
    UNIQUE(model_id, source_role, url),
    FOREIGN KEY (model_id) REFERENCES models(model_id)
);

CREATE INDEX IF NOT EXISTS idx_models_ship_id ON models(ship_id);
CREATE INDEX IF NOT EXISTS idx_files_model_id ON files(model_id);
CREATE INDEX IF NOT EXISTS idx_sources_model_id ON sources(model_id);
