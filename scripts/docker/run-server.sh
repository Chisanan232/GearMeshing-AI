#!/bin/bash
set -e

#
# This script is a router that runs different services based on the SERVICE_TYPE
# environment variable, following duck typing principles for extensibility.
#
# Environment variables:
#
# SERVICE_TYPE → Determines which service to run
#    - "web": Runs the FastAPI web server (default)
#    - "mcp": Runs the MCP server
#    - "webhook": Runs the Slack webhook server
#    - "integrated": Runs either server in integrated mode
#
# For all other environment variables, see the respective server scripts:
# - run-slack-mcp-server.sh
# - run-slack-webhook-server.sh
#
# Example usage:
# # Run web server (default)
# SERVICE_TYPE=web ./run-server.sh
#
# # Run MCP server
# SERVICE_TYPE=mcp ./run-server.sh
#
## Run webhook server
# SERVICE_TYPE=webhook ./run-server.sh
#
## Run integrated server via MCP entry point
# SERVICE_TYPE=integrated ./run-server.sh
#
## Run integrated server via webhook entry point
# SERVICE_TYPE=integrated-webhook ./run-server.sh
#

# Default to web server if SERVICE_TYPE is not set
SERVICE_TYPE=${SERVICE_TYPE:-web}

# Directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Print informational message
echo "SERVICE_TYPE is set to: ${SERVICE_TYPE}"

# Determine which server to run based on SERVICE_TYPE
case "${SERVICE_TYPE}" in
    "web")
        echo "🚀 Starting FastAPI web server..."
        echo "📊 Health check endpoints will be available at:"
        echo "   - http://localhost:8000/health"
        echo "   - http://localhost:8000/health/simple"
        echo "   - http://localhost:8000/health/ready"
        echo "   - http://localhost:8000/health/live"
        echo "📖 API documentation will be available at:"
        echo "   - http://localhost:8000/docs (Swagger)"
        echo "   - http://localhost:8000/redoc (ReDoc)"
        
        # Set default host and port for web server
        HOST=${HOST:-0.0.0.0}
        PORT=${PORT:-8000}
        RELOAD=${RELOAD:-false}
        
        # Build uvicorn command with optional reload flag
        UVICORN_CMD="uv run uvicorn gearmeshing_ai.restapi.main:app --host ${HOST} --port ${PORT} --log-level ${LOG_LEVEL:-info}"
        
        # Add reload flag only if RELOAD is true
        if [ "${RELOAD}" = "true" ] || [ "${RELOAD}" = "1" ]; then
            UVICORN_CMD="${UVICORN_CMD} --reload"
        fi
        
        # Run the FastAPI web server
        echo "🌍 Will set up the server by command line: ${UVICORN_CMD}"
        exec ${UVICORN_CMD}
        ;;
        
    "mcp")
        echo "🔧 Starting MCP server..."
        # Your MCP server startup logic here
        echo "⚠️  MCP server not yet implemented"
        exit 1
        ;;
        
    "webhook")
        echo "🪝 Starting Slack webhook server..."
        # Your webhook server startup logic here
        echo "⚠️  Webhook server not yet implemented"
        exit 1
        ;;
        
    "integrated")
        echo "🔄 Starting integrated server..."
        # Your integrated server startup logic here
        echo "⚠️  Integrated server not yet implemented"
        exit 1
        ;;
        
    *)
        echo "❌ Unknown SERVICE_TYPE: ${SERVICE_TYPE}"
        echo "Supported values: web, mcp, webhook, integrated"
        exit 1
        ;;
esac
