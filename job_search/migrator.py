#!/usr/bin/env python3
"""
Migrate job posting pickle files to DuckDB with a single jobs table.
Supports incremental updates by tracking processed files.
"""

# ruff: noqa: F541
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import duckdb

from job_search.scrape import DS_SF, P_interim_date, read_data


class JobMigrator:
    """Migrates job pickle files to a single DuckDB jobs table."""

    def __init__(self, db_path: str = f"{DS_SF}.duckdb", data_dir: str = P_interim_date / DS_SF):
        self.db_path = db_path
        self.data_dir = Path(data_dir)
        self.conn = duckdb.connect(db_path)
        self._create_schema()

    def _create_schema(self):
        """Create single jobs table schema with indexes."""

        # Single jobs table with all data embedded
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                requisition_id VARCHAR PRIMARY KEY,
                mtime TIMESTAMP,
                job_id VARCHAR NOT NULL,
                board_token VARCHAR,
                source VARCHAR,
                apply_url VARCHAR,
                collapse_key VARCHAR,
                is_expired BOOLEAN,

                -- Job information
                title VARCHAR NOT NULL,
                job_title_raw VARCHAR,
                description TEXT,
                core_job_title VARCHAR,
                requirements_summary TEXT,

                -- Structured data
                technical_tools VARCHAR[],
                licenses_certifications VARCHAR[],
                role_activities VARCHAR[],
                language_requirements VARCHAR[],

                -- Degree requirements
                associates_degree_requirement VARCHAR,
                associates_degree_fields VARCHAR[],
                bachelors_degree_requirement VARCHAR,
                bachelors_degree_fields VARCHAR[],
                masters_degree_requirement VARCHAR,
                masters_degree_fields VARCHAR[],
                doctorate_degree_requirement VARCHAR,
                doctorate_degree_fields VARCHAR[],
                is_high_school_required BOOLEAN,

                -- Experience requirements
                min_industry_role_yoe DECIMAL(5,2),
                is_min_industry_role_yoe_not_mentioned BOOLEAN,
                min_management_leadership_yoe DECIMAL(5,2),
                is_min_management_leadership_yoe_not_mentioned BOOLEAN,

                -- Role details
                job_category VARCHAR,
                commitment VARCHAR[],
                role_type VARCHAR,
                seniority_level VARCHAR,

                -- Workplace
                workplace_type VARCHAR,
                workplace_physical_environment VARCHAR,
                formatted_workplace_location VARCHAR,
                is_workplace_worldwide_ok BOOLEAN,
                workplace_cities VARCHAR[],
                workplace_counties VARCHAR[],
                workplace_states VARCHAR[],
                workplace_countries VARCHAR[],
                workplace_continents VARCHAR[],
                boundless_workplace_states VARCHAR[],
                boundless_workplace_countries VARCHAR[],
                boundless_workplace_continents VARCHAR[],
                number_of_workplace_cities INTEGER,
                number_of_workplace_counties INTEGER,
                number_of_workplace_states INTEGER,
                number_of_workplace_countries INTEGER,
                number_of_workplace_continents INTEGER,

                -- Work conditions
                oral_communication_level VARCHAR,
                physical_labor_intensity VARCHAR,
                physical_position VARCHAR,
                computer_usage VARCHAR,
                cognitive_demand VARCHAR,
                air_travel_requirement VARCHAR,
                land_travel_requirement VARCHAR,
                morning_shift_work VARCHAR,
                evening_shift_work VARCHAR,
                overnight_work VARCHAR,
                on_call_requirement VARCHAR,
                weekend_availability_required BOOLEAN,
                holiday_availability_required BOOLEAN,
                overtime_required BOOLEAN,

                -- Compensation
                yearly_min_compensation DECIMAL(18,2),
                yearly_max_compensation DECIMAL(18,2),
                monthly_min_compensation DECIMAL(18,2),
                monthly_max_compensation DECIMAL(18,2),
                weekly_min_compensation DECIMAL(18,2),
                weekly_max_compensation DECIMAL(18,2),
                hourly_min_compensation DECIMAL(10,2),
                hourly_max_compensation DECIMAL(10,2),
                biweekly_min_compensation DECIMAL(18,2),
                biweekly_max_compensation DECIMAL(18,2),
                daily_min_compensation DECIMAL(18,2),
                daily_max_compensation DECIMAL(18,2),
                is_compensation_transparent BOOLEAN,
                listed_compensation_currency VARCHAR,
                listed_compensation_frequency VARCHAR,

                -- Benefits
                four_oh_one_k_matching BOOLEAN,
                generous_paid_time_off BOOLEAN,
                four_day_work_week BOOLEAN,
                tuition_reimbursement BOOLEAN,
                retirement_plan BOOLEAN,
                generous_parental_leave BOOLEAN,
                fair_chance BOOLEAN,
                visa_sponsorship BOOLEAN,
                relocation_assistance BOOLEAN,
                military_veterans BOOLEAN,

                -- Other
                security_clearance VARCHAR,
                is_driver_license_required BOOLEAN,
                position_employer_type VARCHAR,
                company_sector_and_industry VARCHAR,

                -- Dates
                estimated_publish_date TIMESTAMP,
                estimated_publish_date_millis BIGINT,
                valid_through TIMESTAMP,

                -- User interactions (for reference)
                hidden_from_users VARCHAR[],
                viewed_by_users VARCHAR[],
                applied_from_users VARCHAR[],

                -- Enriched Company data (embedded)
                company_enriched_at TIMESTAMP,
                company_status VARCHAR,
                company_name VARCHAR,
                company_homepage_uri VARCHAR,
                company_hq_country VARCHAR,
                company_parent_company VARCHAR,
                company_subsidiaries VARCHAR[],
                company_industries VARCHAR[],
                company_activities VARCHAR[],
                company_nb_employees INTEGER,
                company_year_founded INTEGER,
                company_tagline VARCHAR,
                company_organization_type VARCHAR,
                company_latest_funding_investors VARCHAR,
                company_latest_funding_type VARCHAR,
                company_latest_funding_year INTEGER,
                company_latest_funding_amount DECIMAL(18,2),
                company_stock_exchange VARCHAR,
                company_stock_symbol VARCHAR,

                -- Location data (embedded as arrays)
                location_latitudes DECIMAL(10,7)[],
                location_longitudes DECIMAL(10,7)[],

                -- Metadata
                created_at TIMESTAMP DEFAULT now(),
                updated_at TIMESTAMP DEFAULT now()
            )
        """)

        # Processed files tracking table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_files (
                file_path VARCHAR PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT now(),
                requisition_id VARCHAR
            )
        """)

        # Create indexes for common search queries
        self._create_indexes()

    def _create_indexes(self):
        """Create indexes optimized for job search queries."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(title)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_core_title ON jobs(core_job_title)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_company_name ON jobs(company_name)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_seniority ON jobs(seniority_level)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_workplace_type ON jobs(workplace_type)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_salary_min ON jobs(yearly_min_compensation)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_salary_max ON jobs(yearly_max_compensation)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_publish_date ON jobs(estimated_publish_date)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_expired ON jobs(is_expired)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_category ON jobs(job_category)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs(job_id)",
        ]

        for idx in indexes:
            try:
                self.conn.execute(idx)
            except Exception:
                pass  # Index may already exist

    def _extract_jobs(self, data: Dict[str, Any], mtime=None) -> list[Optional[Dict[str, Any]]]:
        """Extract list of job data from file."""
        try:
            job_data = data['props']['pageProps']['job']
            jobs = [self._extract_job(job_data, mtime)]
        except KeyError:
            hits = data['pageProps']['hits']
            jobs = [self._extract_job(job_data, mtime) for job_data in hits]
        return jobs

    def _extract_job(self, data: Dict[str, Any], mtime=None) -> Optional[Dict[str, Any]]:
        """Extract all job data from pickle file into a single record."""
        # job = data.get('props', {}).get('pageProps', {}).get('job', {})
        try:
            job = data['props']['pageProps']['job']
        # except KeyError:
        #     job = data['pageProps']['hits'][0]
        except KeyError:
            job = data

        if not job:
            return None
        if mtime is None:
            mtime = datetime.now().replace(microsecond=0)

        job_info = job.get('job_information', {})
        v5_processed = job.get('v5_processed_job_data', {})
        v5_company_data = job.get('v5_processed_company_data', {})
        company_data = job.get('enriched_company_data', {})
        geolocations = job.get('_geoloc', [])

        # Extract location arrays
        latitudes = [geo.get('lat') for geo in geolocations if geo.get('lat')]
        longitudes = [geo.get('lon') for geo in geolocations if geo.get('lon')]

        _v5_is_public = v5_company_data.get('is_public')
        _v5_org_type = {True: 'Public', False: 'Private'}.get(_v5_is_public)
        if v5_company_data.get('is_non_profit'):
            _v5_org_type = 'Non-Profit'

        _estimated_publish_date = v5_processed.get('estimated_publish_date')
        if isinstance(_estimated_publish_date, int):
            _estimated_publish_date = datetime.fromtimestamp(_estimated_publish_date / 1000)

        return {
            'requisition_id': job.get('requisition_id'),
            'mtime': mtime,
            'job_id': job.get('id'),
            'board_token': job.get('board_token'),
            'source': job.get('source'),
            'apply_url': job.get('apply_url'),
            'collapse_key': job.get('collapse_key'),
            'is_expired': job.get('is_expired'),

            # Job information
            'title': job_info.get('title'),
            'job_title_raw': job_info.get('job_title_raw'),
            'description': job_info.get('description'),
            'core_job_title': v5_processed.get('core_job_title'),
            'requirements_summary': v5_processed.get('requirements_summary'),

            # Structured data
            'technical_tools': v5_processed.get('technical_tools', []),
            'licenses_certifications': v5_processed.get('licenses_or_certifications', []),
            'role_activities': v5_processed.get('role_activities', []),
            'language_requirements': v5_processed.get('language_requirements', []),

            # Degree requirements
            'associates_degree_requirement': v5_processed.get('associates_degree_requirement'),
            'associates_degree_fields': v5_processed.get('associates_degree_fields_of_study', []),
            'bachelors_degree_requirement': v5_processed.get('bachelors_degree_requirement'),
            'bachelors_degree_fields': v5_processed.get('bachelors_degree_fields_of_study', []),
            'masters_degree_requirement': v5_processed.get('masters_degree_requirement'),
            'masters_degree_fields': v5_processed.get('masters_degree_fields_of_study', []),
            'doctorate_degree_requirement': v5_processed.get('doctorate_degree_requirement'),
            'doctorate_degree_fields': v5_processed.get('doctorate_degree_fields_of_study', []),
            'is_high_school_required': v5_processed.get('is_high_school_required'),

            # Experience requirements
            'min_industry_role_yoe': v5_processed.get('min_industry_and_role_yoe'),
            'is_min_industry_role_yoe_not_mentioned': v5_processed.get('is_min_industry_and_role_yoe_not_mentioned'),
            'min_management_leadership_yoe': v5_processed.get('min_management_and_leadership_yoe'),
            'is_min_management_leadership_yoe_not_mentioned': v5_processed.get('is_min_management_and_leadership_yoe_not_mentioned'),

            # Role details
            'job_category': v5_processed.get('job_category'),
            'commitment': v5_processed.get('commitment', []),
            'role_type': v5_processed.get('role_type'),
            'seniority_level': v5_processed.get('seniority_level'),

            # Workplace
            'workplace_type': v5_processed.get('workplace_type'),
            'workplace_physical_environment': v5_processed.get('workplace_physical_environment'),
            'formatted_workplace_location': v5_processed.get('formatted_workplace_location'),
            'is_workplace_worldwide_ok': v5_processed.get('is_workplace_worldwide_ok'),
            'workplace_cities': v5_processed.get('workplace_cities', []),
            'workplace_counties': v5_processed.get('workplace_counties', []),
            'workplace_states': v5_processed.get('workplace_states', []),
            'workplace_countries': v5_processed.get('workplace_countries', []),
            'workplace_continents': v5_processed.get('workplace_continents', []),
            'boundless_workplace_states': v5_processed.get('boundless_workplace_states', []),
            'boundless_workplace_countries': v5_processed.get('boundless_workplace_countries', []),
            'boundless_workplace_continents': v5_processed.get('boundless_workplace_continents', []),
            'number_of_workplace_cities': v5_processed.get('number_of_workplace_cities'),
            'number_of_workplace_counties': v5_processed.get('number_of_workplace_counties'),
            'number_of_workplace_states': v5_processed.get('number_of_workplace_states'),
            'number_of_workplace_countries': v5_processed.get('number_of_workplace_countries'),
            'number_of_workplace_continents': v5_processed.get('number_of_workplace_continents'),

            # Work conditions
            'oral_communication_level': v5_processed.get('oral_communication_level'),
            'physical_labor_intensity': v5_processed.get('physical_labor_intensity'),
            'physical_position': v5_processed.get('physical_position'),
            'computer_usage': v5_processed.get('computer_usage'),
            'cognitive_demand': v5_processed.get('cognitive_demand'),
            'air_travel_requirement': v5_processed.get('air_travel_requirement'),
            'land_travel_requirement': v5_processed.get('land_travel_requirement'),
            'morning_shift_work': v5_processed.get('morning_shift_work'),
            'evening_shift_work': v5_processed.get('evening_shift_work'),
            'overnight_work': v5_processed.get('overnight_work'),
            'on_call_requirement': v5_processed.get('on_call_requirement'),
            'weekend_availability_required': v5_processed.get('weekend_availability_required'),
            'holiday_availability_required': v5_processed.get('holiday_availability_required'),
            'overtime_required': v5_processed.get('overtime_required'),

            # Compensation
            'yearly_min_compensation': v5_processed.get('yearly_min_compensation'),
            'yearly_max_compensation': v5_processed.get('yearly_max_compensation'),
            'monthly_min_compensation': v5_processed.get('monthly_min_compensation'),
            'monthly_max_compensation': v5_processed.get('monthly_max_compensation'),
            'weekly_min_compensation': v5_processed.get('weekly_min_compensation'),
            'weekly_max_compensation': v5_processed.get('weekly_max_compensation'),
            'hourly_min_compensation': v5_processed.get('hourly_min_compensation'),
            'hourly_max_compensation': v5_processed.get('hourly_max_compensation'),
            'biweekly_min_compensation': v5_processed.get('bi-weekly_min_compensation'),
            'biweekly_max_compensation': v5_processed.get('bi-weekly_max_compensation'),
            'daily_min_compensation': v5_processed.get('daily_min_compensation'),
            'daily_max_compensation': v5_processed.get('daily_max_compensation'),
            'is_compensation_transparent': v5_processed.get('is_compensation_transparent'),
            'listed_compensation_currency': v5_processed.get('listed_compensation_currency'),
            'listed_compensation_frequency': v5_processed.get('listed_compensation_frequency'),

            # Benefits
            'four_oh_one_k_matching': v5_processed.get('401k_matching'),
            'generous_paid_time_off': v5_processed.get('generous_paid_time_off'),
            'four_day_work_week': v5_processed.get('four_day_work_week'),
            'tuition_reimbursement': v5_processed.get('tuition_reimbursement'),
            'retirement_plan': v5_processed.get('retirement_plan'),
            'generous_parental_leave': v5_processed.get('generous_parental_leave'),
            'fair_chance': v5_processed.get('fair_chance'),
            'visa_sponsorship': v5_processed.get('visa_sponsorship'),
            'relocation_assistance': v5_processed.get('relocation_assistance'),
            'military_veterans': v5_processed.get('military_veterans'),

            # Other
            'security_clearance': v5_processed.get('security_clearance'),
            'is_driver_license_required': v5_processed.get('is_driver_license_required'),
            'position_employer_type': v5_processed.get('position_employer_type'),
            'company_sector_and_industry': v5_processed.get('company_sector_and_industry'),

            # Dates
            'estimated_publish_date': _estimated_publish_date,
            'estimated_publish_date_millis': v5_processed.get('estimated_publish_date_millis'),
            'valid_through': data.get('props', {}).get('pageProps', {}).get('validThrough'),

            # User interactions
            'hidden_from_users': job_info.get('hiddenFromUsers', []),
            'viewed_by_users': job_info.get('viewedByUsers', []),
            'applied_from_users': job_info.get('appliedFromUsers', []),

            # Enriched Company data (embedded)
            'company_enriched_at': company_data.get('enriched_at'),
            'company_status': company_data.get('status'),
            'company_name': company_data.get('name') or v5_processed.get('company_name') or v5_company_data.get('name'),
            'company_homepage_uri': company_data.get('homepage_uri') or v5_processed.get('company_website') or v5_company_data.get('website'),
            'company_hq_country': company_data.get('hq_country') or v5_company_data.get('headquarters_country'),
            'company_parent_company': company_data.get('parent_company') or v5_company_data.get('parent_company'),
            'company_subsidiaries': company_data.get('subsidiaries') or v5_company_data.get('subsidiaries'),
            'company_industries': company_data.get('industries') or v5_company_data.get('industries'),
            'company_activities': company_data.get('activities') or v5_processed.get('company_activities') or v5_company_data.get('activities'),
            'company_nb_employees': company_data.get('nb_employees') or v5_company_data.get('number_employees'),
            'company_year_founded': company_data.get('year_founded') or v5_company_data.get('year_founded'),
            'company_tagline': company_data.get('tagline') or v5_processed.get('tagline') or v5_company_data.get('tagline'),
            'company_organization_type': company_data.get('organization_type') or _v5_org_type,
            'company_latest_funding_investors': company_data.get('latest_funding_investors') or v5_company_data.get('investors'),
            'company_latest_funding_type': company_data.get('latest_funding_type') or v5_company_data.get('latest_funding_series'),
            'company_latest_funding_year': company_data.get('latest_funding_year') or v5_company_data.get('latest_funding_year'),
            'company_latest_funding_amount': company_data.get('latest_funding_amount') or v5_company_data.get('latest_funding_amount'),
            'company_stock_exchange': company_data.get('stock_exchange') or v5_company_data.get('stock_exchange'),
            'company_stock_symbol': company_data.get('stock_symbol') or v5_company_data.get('stock_exchange'),

            # Location data (embedded)
            'location_latitudes': latitudes,
            'location_longitudes': longitudes,
        }

    def _is_file_processed(self, file_path: Path) -> bool:
        """Check if file has already been processed."""
        result = self.conn.execute(
            "SELECT 1 FROM processed_files WHERE file_path = ?",
            [str(file_path)]
        ).fetchone()
        return result is not None

    def _mark_file_processed(self, file_path: Path, requisition_id: str):
        """Mark file as processed."""
        self.conn.execute(
            "INSERT INTO processed_files (file_path, requisition_id) VALUES (?, ?)",
            [str(file_path), requisition_id]
        )

    def _insert_job(self, job: Dict[str, Any]):
        """Insert or update job record."""
        self.conn.execute("""
            INSERT INTO jobs VALUES (
                $requisition_id, $mtime,
                $job_id, $board_token, $source, $apply_url,
                $collapse_key, $is_expired, $title, $job_title_raw, $description,
                $core_job_title, $requirements_summary, $technical_tools,
                $licenses_certifications, $role_activities, $language_requirements,
                $associates_degree_requirement, $associates_degree_fields,
                $bachelors_degree_requirement, $bachelors_degree_fields,
                $masters_degree_requirement, $masters_degree_fields,
                $doctorate_degree_requirement, $doctorate_degree_fields,
                $is_high_school_required, $min_industry_role_yoe,
                $is_min_industry_role_yoe_not_mentioned, $min_management_leadership_yoe,
                $is_min_management_leadership_yoe_not_mentioned, $job_category,
                $commitment, $role_type, $seniority_level, $workplace_type,
                $workplace_physical_environment, $formatted_workplace_location,
                $is_workplace_worldwide_ok, $workplace_cities, $workplace_counties,
                $workplace_states, $workplace_countries, $workplace_continents,
                $boundless_workplace_states, $boundless_workplace_countries,
                $boundless_workplace_continents, $number_of_workplace_cities,
                $number_of_workplace_counties, $number_of_workplace_states,
                $number_of_workplace_countries, $number_of_workplace_continents,
                $oral_communication_level, $physical_labor_intensity, $physical_position,
                $computer_usage, $cognitive_demand, $air_travel_requirement,
                $land_travel_requirement, $morning_shift_work, $evening_shift_work,
                $overnight_work, $on_call_requirement, $weekend_availability_required,
                $holiday_availability_required, $overtime_required,
                $yearly_min_compensation, $yearly_max_compensation,
                $monthly_min_compensation, $monthly_max_compensation,
                $weekly_min_compensation, $weekly_max_compensation,
                $hourly_min_compensation, $hourly_max_compensation,
                $biweekly_min_compensation, $biweekly_max_compensation,
                $daily_min_compensation, $daily_max_compensation,
                $is_compensation_transparent, $listed_compensation_currency,
                $listed_compensation_frequency, $four_oh_one_k_matching,
                $generous_paid_time_off, $four_day_work_week, $tuition_reimbursement,
                $retirement_plan, $generous_parental_leave, $fair_chance,
                $visa_sponsorship, $relocation_assistance, $military_veterans,
                $security_clearance, $is_driver_license_required, $position_employer_type,
                $company_sector_and_industry,
                $estimated_publish_date, $estimated_publish_date_millis, $valid_through,
                $hidden_from_users, $viewed_by_users, $applied_from_users,
                $company_enriched_at,
                $company_status,
                $company_name,
                $company_homepage_uri,
                $company_hq_country,
                $company_parent_company,
                $company_subsidiaries,
                $company_industries,
                $company_activities,
                $company_nb_employees,
                $company_year_founded,
                $company_tagline,
                $company_organization_type,
                $company_latest_funding_investors,
                $company_latest_funding_type,
                $company_latest_funding_year,
                $company_latest_funding_amount,
                $company_stock_exchange,
                $company_stock_symbol,
                $location_latitudes, $location_longitudes,
                now(), now()
            )
            ON CONFLICT (requisition_id) DO UPDATE SET
                is_expired = EXCLUDED.is_expired,
                updated_at = now()
        """, job)

    def process_file(self, file_path: Path) -> int:
        """Process a single pickle file."""
        try:
            # Check if already processed
            if self._is_file_processed(file_path):
                return 0

            # Load json.gz or pickle file
            data = read_data(file_path)

            # Extract data
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            jobs = self._extract_jobs(data, mtime)
            for job in jobs:
                if not job or not job.get('requisition_id'):
                    print(f"Skipping {file_path}: no valid job data")
                    continue
                    # return 0

                # Insert into database
                self._insert_job(job)

            # Mark as processed
            self._mark_file_processed(file_path, job['requisition_id'])

            return len(jobs)

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return 0

    def migrate_all(self, skip_processed: bool = True) -> Dict[str, int]:
        """Migrate all pickle files in the data directory."""
        stats = {'jobs': 0, 'processed': 0, 'skipped': 0, 'errors': 0}

        # Find all pickle files
        pickle_files = list(self.data_dir.rglob("*.pkl"))
        total = len(pickle_files)

        print(f"Found {total} pickle files")

        for i, file_path in enumerate(pickle_files, 1):
            if skip_processed and self._is_file_processed(file_path):
                stats['skipped'] += 1
            else:
                if (N_jobs := self.process_file(file_path)):
                    stats['jobs'] += N_jobs
                    stats['processed'] += 1
                else:
                    stats['errors'] += 1

            if i % 100 == 0:
                print(f"Progress: {i}/{total} pickle files ({stats['processed']} processed, {stats['skipped']} skipped, {stats['errors']} errors)")

        # Find all json files
        json_files = list(self.data_dir.rglob("*.json.gz"))
        total = len(json_files)
        print(f"Found {total} json files")

        for i, file_path in enumerate(json_files, 1):
            if skip_processed and self._is_file_processed(file_path):
                stats['skipped'] += 1
            else:
                if (N_jobs := self.process_file(file_path)):
                    stats['jobs'] += N_jobs
                    stats['processed'] += 1
                else:
                    stats['errors'] += 1

            # if i % 100 == 0:
            print(f"Progress: {i}/{total} json files ({stats['jobs']} jobs, {stats['processed']} processed, {stats['skipped']} skipped, {stats['errors']} errors)")

        print(f"\nMigration complete!")
        print(f"  Jobs:      {stats['jobs']}")
        print(f"  Processed: {stats['processed']}")
        print(f"  Skipped:   {stats['skipped']}")
        print(f"  Errors:    {stats['errors']}")

        return stats

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return {
            'total_jobs': self.conn.sql("SELECT COUNT(*) FROM jobs").fetchone()[0],
            'active_jobs': self.conn.sql("SELECT COUNT(*) FROM jobs WHERE is_expired = false").fetchone()[0],
            'expired_jobs': self.conn.sql("SELECT COUNT(*) FROM jobs WHERE is_expired = true").fetchone()[0],
            'processed_files': self.conn.sql("SELECT COUNT(*) FROM processed_files").fetchone()[0],
        }

    def close(self):
        """Close database connection."""
        self.conn.close()


def main():
    """Main migration script."""
    import sys

    from job_search.scrape import DS_SF, HEALTH, P_interim_date

    # Parse arguments
    db_path = sys.argv[1] if len(sys.argv) > 1 else DS_SF
    if db_path == "DS_SF":
        db_path = DS_SF
    if db_path == "HEALTH":
        db_path = HEALTH
    # data_dir = sys.argv[2] if len(sys.argv) > 2 else P_interim_date / DS_SF
    data_dir = sys.argv[2] if len(sys.argv) > 2 else P_interim_date / db_path
    if not db_path.endswith('.duckdb'):
        db_path = f"{db_path}.duckdb"

    print(f"Starting migration to {db_path}")
    print(f"Reading from {data_dir}")

    migrator = JobMigrator(db_path=db_path, data_dir=data_dir)

    try:
        # Run migration
        _stats = migrator.migrate_all(skip_processed=True)

        # Show final stats
        db_stats = migrator.get_stats()
        print("\nDatabase Statistics:")
        for key, value in db_stats.items():
            print(f"  {key}: {value}")

    finally:
        migrator.close()


if __name__ == "__main__":
    main()
