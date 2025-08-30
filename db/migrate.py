"""
Database migration runner
Handles database migrations and schema management
"""

import os
import sys
import logging
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import DatabaseConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationRunner:
    """Handles database migrations"""
    
    def __init__(self):
        self.db_uri = DatabaseConfig.get_database_uri()
        self.migrations_dir = Path(__file__).parent / 'migrations'
        self.schema_file = Path(__file__).parent / 'schema.sql'
        
    def get_connection(self, database=None):
        """Get database connection"""
        if database:
            # Connect to specific database
            uri = self.db_uri.rsplit('/', 1)[0] + f'/{database}'
        else:
            uri = self.db_uri
            
        return psycopg2.connect(uri)
    
    def create_database(self):
        """Create database if it doesn't exist"""
        db_name = self.db_uri.split('/')[-1].split('?')[0]
        
        try:
            # Connect to postgres database
            conn = self.get_connection('postgres')
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()
            
            # Check if database exists
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (db_name,)
            )
            
            if not cur.fetchone():
                cur.execute(f"CREATE DATABASE {db_name}")
                logger.info(f"Created database: {db_name}")
            else:
                logger.info(f"Database already exists: {db_name}")
                
            cur.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            raise
    
    def create_migration_table(self):
        """Create migration tracking table"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER,
                success BOOLEAN DEFAULT TRUE,
                error_message TEXT
            )
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info("Migration tracking table ready")
    
    def get_executed_migrations(self):
        """Get list of already executed migrations"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT version FROM schema_migrations 
            WHERE success = TRUE 
            ORDER BY version
        """)
        
        executed = [row[0] for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return executed
    
    def execute_schema_file(self):
        """Execute the complete schema.sql file"""
        if not self.schema_file.exists():
            logger.error(f"Schema file not found: {self.schema_file}")
            return False
            
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            # Read and execute schema file
            with open(self.schema_file, 'r') as f:
                schema_sql = f.read()
                
            # Execute the schema
            cur.execute(schema_sql)
            conn.commit()
            
            logger.info("Schema successfully applied")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error applying schema: {e}")
            return False
            
        finally:
            cur.close()
            conn.close()
    
    def run_migration(self, migration_file):
        """Run a single migration file"""
        import importlib.util
        
        # Load migration module
        spec = importlib.util.spec_from_file_location(
            migration_file.stem,
            migration_file
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        
        conn = self.get_connection()
        cur = conn.cursor()
        
        start_time = datetime.now()
        
        try:
            # Run upgrade function
            migration.upgrade()
            
            # Record successful migration
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            cur.execute("""
                INSERT INTO schema_migrations (version, execution_time_ms, success)
                VALUES (%s, %s, %s)
            """, (migration_file.stem, execution_time, True))
            
            conn.commit()
            logger.info(f"Successfully ran migration: {migration_file.stem}")
            return True
            
        except Exception as e:
            conn.rollback()
            
            # Record failed migration
            cur.execute("""
                INSERT INTO schema_migrations (version, success, error_message)
                VALUES (%s, %s, %s)
            """, (migration_file.stem, False, str(e)))
            
            conn.commit()
            logger.error(f"Failed to run migration {migration_file.stem}: {e}")
            return False
            
        finally:
            cur.close()
            conn.close()

    def run_all_migrations(self):
        """Run all pending migrations"""
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return
        
        # Get executed migrations
        executed = self.get_executed_migrations()
        
        # Get all migration files
        migration_files = sorted(self.migrations_dir.glob('*.py'))
        
        # Run pending migrations
        pending_count = 0
        for migration_file in migration_files:
            if migration_file.stem not in executed:
                logger.info(f"Running migration: {migration_file.stem}")
                if self.run_migration(migration_file):
                    pending_count += 1
                else:
                    logger.error(f"Migration failed, stopping execution")
                    break
        
        if pending_count == 0:
            logger.info("No pending migrations to run")
        else:
            logger.info(f"Ran {pending_count} migration(s)")
    
    def rollback_migration(self, version):
        """Rollback a specific migration"""
        import importlib.util
        
        migration_file = self.migrations_dir / f"{version}.py"
        if not migration_file.exists():
            logger.error(f"Migration file not found: {migration_file}")
            return False
        
        # Load migration module
        spec = importlib.util.spec_from_file_location(version, migration_file)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            # Run downgrade function
            migration.downgrade()
            
            # Remove from migration table
            cur.execute("""
                DELETE FROM schema_migrations WHERE version = %s
            """, (version,))
            
            conn.commit()
            logger.info(f"Successfully rolled back migration: {version}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to rollback migration {version}: {e}")
            return False
            
        finally:
            cur.close()
            conn.close()
    
    def get_migration_status(self):
        """Get status of all migrations"""
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                version,
                executed_at,
                execution_time_ms,
                success,
                error_message
            FROM schema_migrations
            ORDER BY executed_at DESC
        """)
        
        migrations = []
        for row in cur.fetchall():
            migrations.append({
                'version': row[0],
                'executed_at': row[1].isoformat() if row[1] else None,
                'execution_time_ms': row[2],
                'success': row[3],
                'error_message': row[4]
            })
        
        cur.close()
        conn.close()
        
        return migrations
    
    def reset_database(self):
        """Reset database - drop all tables and reapply schema"""
        if input("This will DELETE ALL DATA. Are you sure? (yes/no): ").lower() != 'yes':
            logger.info("Reset cancelled")
            return
        
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            # Get all tables
            cur.execute("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
            """)
            
            tables = [row[0] for row in cur.fetchall()]
            
            # Drop all tables
            for table in tables:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                logger.info(f"Dropped table: {table}")
            
            conn.commit()
            
            # Reapply schema
            if self.execute_schema_file():
                logger.info("Database reset completed successfully")
            else:
                logger.error("Failed to reapply schema")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error resetting database: {e}")
            
        finally:
            cur.close()
            conn.close()

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='Database Migration Tool')
    parser.add_argument(
        'command',
        choices=['create', 'migrate', 'rollback', 'status', 'reset', 'schema'],
        help='Migration command to run'
    )
    parser.add_argument(
        '--version',
        help='Migration version (for rollback)'
    )
    
    args = parser.parse_args()
    
    runner = MigrationRunner()
    
    if args.command == 'create':
        # Create database and migration table
        runner.create_database()
        runner.create_migration_table()
        
    elif args.command == 'migrate':
        # Run pending migrations
        runner.create_migration_table()
        runner.run_all_migrations()
        
    elif args.command == 'rollback':
        # Rollback specific migration
        if not args.version:
            logger.error("Version required for rollback")
            sys.exit(1)
        runner.rollback_migration(args.version)
        
    elif args.command == 'status':
        # Show migration status
        migrations = runner.get_migration_status()
        
        if migrations:
            print("\nMigration Status:")
            print("-" * 80)
            for m in migrations:
                status = "✓" if m['success'] else "✗"
                print(f"{status} {m['version']:<30} {m['executed_at']:<20}")
                if m['error_message']:
                    print(f"  Error: {m['error_message']}")
        else:
            print("No migrations have been run")
            
    elif args.command == 'reset':
        # Reset database
        runner.reset_database()
        
    elif args.command == 'schema':
        # Apply schema.sql directly
        runner.create_database()
        if runner.execute_schema_file():
            logger.info("Schema applied successfully")
        else:
            logger.error("Failed to apply schema")
            sys.exit(1)

if __name__ == '__main__':
    main()