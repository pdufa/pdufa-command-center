-- Additive schema for the isolated new platform only.

CREATE TABLE IF NOT EXISTS full_trial_records (
	nct_id VARCHAR(11) NOT NULL, 
	payload_gzip BYTEA NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	summary JSON NOT NULL, 
	statistics JSON NOT NULL, 
	fetched_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (nct_id)
);

CREATE TABLE IF NOT EXISTS full_trial_download (
	id SERIAL NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	scope_ids JSON NOT NULL, 
	completed_ids JSON NOT NULL, 
	missing_ids JSON NOT NULL, 
	statistics_count INTEGER NOT NULL, 
	p_value_count INTEGER NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	lease_owner VARCHAR(40) NOT NULL, 
	lease_until TIMESTAMP WITH TIME ZONE, 
	error VARCHAR(300) NOT NULL, 
	PRIMARY KEY (id)
);
