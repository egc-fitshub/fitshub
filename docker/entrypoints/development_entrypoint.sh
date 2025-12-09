#!/bin/bash

# ---------------------------------------------------------------------------
# Creative Commons CC BY 4.0 - David Romero - Diverso Lab
# ---------------------------------------------------------------------------
# This script is licensed under the Creative Commons Attribution 4.0 
# International License. You are free to share and adapt the material 
# as long as appropriate credit is given, a link to the license is provided, 
# and you indicate if changes were made.
#
# For more details, visit:
# https://creativecommons.org/licenses/by/4.0/
# ---------------------------------------------------------------------------

# Exit immediately if a command exits with a non-zero status
set -e

wait_for_elasticsearch_green() {
    local es_url="${ELASTICSEARCH_HOST:-http://elasticsearch:9200}"
    local trimmed_url="${es_url%/}"
    local health_endpoint="${trimmed_url}/_cluster/health"

    echo "Waiting for Elasticsearch at ${trimmed_url} to reach green status..."

    until curl -fsSL "${health_endpoint}" | grep -q '"status":"green"'; do
        echo "Elasticsearch is not green yet. Retrying in 5 seconds..."
        sleep 5
    done

    echo "Elasticsearch cluster is green."
}

# Install Rosemary
pip install -e ./

# Wait for the database to be ready by running a script
sh ./scripts/wait-for-db.sh

# Create a specific database for testing by running a script
sh ./scripts/init-testing-db.sh

# Initialize migrations only if the migrations directory doesn't exist
if [ ! -d "migrations/versions" ]; then
    # Initialize the migration repository
    flask db init
    flask db migrate
fi

# Check if the database is empty
if [ $(mariadb -u $MARIADB_USER -p$MARIADB_PASSWORD -h $MARIADB_HOSTNAME -P $MARIADB_PORT -D $MARIADB_DATABASE -sse "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '$MARIADB_DATABASE';") -eq 0 ]; then
 
    echo "Empty database, migrating..."

    # Get the latest migration revision
    LATEST_REVISION=$(ls -1 migrations/versions/*.py | grep -v "__pycache__" | sort -r | head -n 1 | sed 's/.*\/\(.*\)\.py/\1/')

    echo "Latest revision: $LATEST_REVISION"

    # Run the migration process to apply all database schema changes
    flask db upgrade

    # Seed the database with initial data
    rosemary db:seed -y

else

    echo "Database already initialized, updating migrations..."

    # Get the current revision to avoid duplicate stamp
    CURRENT_REVISION=$(mariadb -u $MARIADB_USER -p$MARIADB_PASSWORD -h $MARIADB_HOSTNAME -P $MARIADB_PORT -D $MARIADB_DATABASE -sse "SELECT version_num FROM alembic_version LIMIT 1;")
    
    if [ -z "$CURRENT_REVISION" ]; then
        # If no current revision, stamp with the latest revision
        flask db stamp head
    fi

    # Run the migration process to apply all database schema changes
    flask db upgrade
fi

wait_for_elasticsearch_green

echo "Creating/refreshing the search index with initial data..."
flask shell <<'PY'
from app.modules.elasticsearch.utils import init_search_index, reindex_all

init_search_index()
reindex_all()
PY


# Start the Flask application with specified host and port, enabling reload and debug mode
exec flask run --host=0.0.0.0 --port=5000 --reload --debug
