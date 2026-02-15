#!/bin/bash
set -e

echo "🚀 Starting Ashnova project setup..."
echo ""
echo "Note: Core tools (AWS CLI, Azure CLI, GitHub CLI, Pulumi, Node.js, Python, Git, Docker)"
echo "      are provided by devcontainer features. This script handles:"
echo "      - Google Cloud CLI (no official feature available)"
echo "      - Project-specific tools (PostgreSQL, MinIO, dnsutils, jq)"
echo "      - Python virtual environments and dependencies"
echo ""

# Fix for yarn list issue if it exists (inherited from previous config)
if [ -f "/etc/apt/sources.list.d/yarn.list" ]; then
   sudo rm -f /etc/apt/sources.list.d/yarn.list
fi

# Install Google Cloud CLI
if ! command -v gcloud &> /dev/null; then
    echo "📦 Installing Google Cloud CLI..."
    sudo apt-get update
    sudo apt-get install -y apt-transport-https ca-certificates gnupg curl

    if [ ! -f /usr/share/keyrings/cloud.google.gpg ]; then
        curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
    fi

    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list

    sudo apt-get update
    sudo apt-get install -y google-cloud-cli
else
    echo "✅ Google Cloud CLI is already installed."
fi

# Install PostgreSQL Client
if ! command -v psql &> /dev/null; then
    echo "📦 Installing PostgreSQL client..."
    sudo apt-get update
    sudo apt-get install -y postgresql-client
else
    echo "✅ PostgreSQL client is already installed."
fi

# Install MinIO Client (mc)
if ! command -v mc &> /dev/null; then
    echo "📦 Installing MinIO Client (mc)..."
    curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /tmp/mc
    sudo mv /tmp/mc /usr/local/bin/mc
    sudo chmod +x /usr/local/bin/mc
else
    echo "✅ MinIO Client (mc) is already installed."
fi

# Install DNS Utils (dig, host, nslookup)
if ! command -v dig &> /dev/null; then
    echo "📦 Installing dnsutils..."
    sudo apt-get update
    sudo apt-get install -y dnsutils
else
    echo "✅ dnsutils is already installed."
fi

# Install jq (JSON processor)
if ! command -v jq &> /dev/null; then
    echo "📦 Installing jq..."
    sudo apt-get update
    sudo apt-get install -y jq
else
    echo "✅ jq is already installed."
fi

# Install global python tools
echo "📦 Installing global Python tools..."
pip install --upgrade pip
pip install dnspython black flake8 mypy isort pytest

# Function to setup venv
setup_venv() {
    local DIR=$1
    local EXTRA_PIP=$2
    
    if [ -d "$DIR" ]; then
        echo "🔧 Setting up venv for $DIR..."
        
        # Remove existing venv if it exists (to handle Python version changes)
        if [ -d "$DIR/.venv" ]; then
            echo "  ♻️  Removing existing venv..."
            rm -rf "$DIR/.venv"
        fi
        
        # Create new venv
        python3 -m venv "$DIR/.venv"
        
        # Activate and install dependencies
        source "$DIR/.venv/bin/activate"
        pip install --upgrade pip
        
        if [ -f "$DIR/requirements.txt" ]; then
            pip install -r "$DIR/requirements.txt"
        fi
        
        if [ ! -z "$EXTRA_PIP" ]; then
            pip install $EXTRA_PIP
        fi
        
        deactivate
    fi
}

echo ""
echo "=========================================="
echo "📁 Setting up v3 environments (ACTIVE)..."
echo "=========================================="

# Setup v3 API Service (api_v2)
setup_venv "/workspaces/ashnova/ashnova.v3/services/api_v2"

# Setup v3 Web Service (SSR)
setup_venv "/workspaces/ashnova/ashnova.v3/services/web"

echo ""
echo "=========================================="
echo "📁 Setting up v1 environments (legacy)..."
echo "=========================================="

# Setup v1 Infra environments (only if directory exists)
if [ -d "/workspaces/ashnova/ashnova.v1/simple-sns" ]; then
    setup_venv "/workspaces/ashnova/ashnova.v1/simple-sns" "pulumi-aws"
fi

echo ""
echo "=========================================="
echo "📁 Setting up multicloud-auto-deploy..."
echo "=========================================="

# Setup multicloud-auto-deploy backend
if [ -d "/workspaces/ashnova/multicloud-auto-deploy/services/backend" ]; then
    echo "🔧 Setting up multicloud-auto-deploy backend..."
    BACKEND_DIR="/workspaces/ashnova/multicloud-auto-deploy/services/backend"
    
    if [ -d "$BACKEND_DIR/.venv" ]; then
        echo "  ♻️  Removing existing venv..."
        rm -rf "$BACKEND_DIR/.venv"
    fi
    
    python3.12 -m venv "$BACKEND_DIR/.venv"
    source "$BACKEND_DIR/.venv/bin/activate"
    pip install --upgrade pip
    
    if [ -f "$BACKEND_DIR/requirements.txt" ]; then
        pip install -r "$BACKEND_DIR/requirements.txt"
    fi
    
    deactivate
    echo "  ✅ Backend environment ready"
fi

# Setup multicloud-auto-deploy frontend
if [ -d "/workspaces/ashnova/multicloud-auto-deploy/services/frontend" ]; then
    echo "🔧 Setting up multicloud-auto-deploy frontend..."
    FRONTEND_DIR="/workspaces/ashnova/multicloud-auto-deploy/services/frontend"
    
    if [ -d "$FRONTEND_DIR/node_modules" ]; then
        cd "$FRONTEND_DIR"
        npm install
        cd - > /dev/null
        echo "  ✅ Frontend dependencies installed"
    fi
fi

echo ""
echo "=========================================="
echo "📁 Setting up v2 environments (legacy)..."
echo "=========================================="

# Setup v2 Service environments (only if directories exist)
if [ -d "/workspaces/ashnova/ashnova.v2/services/simple_sns_api" ]; then
    setup_venv "/workspaces/ashnova/ashnova.v2/services/simple_sns_api"
fi

if [ -d "/workspaces/ashnova/ashnova.v2/services/simple_sns_web" ]; then
    setup_venv "/workspaces/ashnova/ashnova.v2/services/simple_sns_web"
fi

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "🎯 Quick Start for v3 (Docker Compose):"
echo "  cd /workspaces/ashnova/ashnova.v3"
echo "  docker compose up -d              # Start all services"
echo "  docker compose ps                 # Check status"
echo ""
echo "� Quick Start for multicloud-auto-deploy:"
echo "  cd /workspaces/ashnova/multicloud-auto-deploy"
echo "  # Test local deployments:"
echo "  curl https://52z731x570.execute-api.ap-northeast-1.amazonaws.com/"
echo "  curl https://mcad-staging-api--0000003.livelycoast-fa9d3350.japaneast.azurecontainerapps.io/"
echo "  curl https://mcad-staging-api-son5b3ml7a-an.a.run.app/"
echo ""
echo "📦 Services:"
echo "  • API (FastAPI):      http://localhost:8000"
echo "  • Web App (SSR):      http://localhost:8080"
echo "  • API Docs:           http://localhost:8000/docs"
echo "  • Static Site:        http://localhost:5173"
echo "  • MinIO Console:      http://localhost:9001"
echo ""
echo "☁️  Multi-Cloud Deployments:"
echo "  • AWS (ap-northeast-1):  https://dx3l4mbwg1ade.cloudfront.net"
echo "  • Azure (japaneast):     (Container Apps)"
echo "  • GCP (asia-northeast1): (Cloud Run)"
echo ""
echo "🔑 Login (local dev mode):"
echo "  1. Open http://localhost:8080"
echo "  2. Click 'Login' and enter any username"
echo "  3. Start posting!"
echo ""
echo "🐛 Useful commands:"
echo "  docker compose logs -f api        # View API logs"
echo "  docker compose logs -f web        # View Web logs"
echo "  docker compose restart api web    # Restart services"
echo ""

# Check if Docker Compose services are running
if command -v docker &> /dev/null; then
    cd /workspaces/ashnova/ashnova.v3 2>/dev/null || true
    if [ -f "docker-compose.yml" ]; then
        echo "🔍 Docker Compose status:"
        docker compose ps 2>/dev/null || echo "  Services not running. Run 'docker compose up -d' to start."
        echo ""
    fi
fi

# Check if static site is running
if ! curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "💡 Tip: To start the static site:"
    echo "  cd /workspaces/ashnova/ashnova.v3/static-site"
    echo "  python3 -m http.server 5173 &"
    echo ""
fi
