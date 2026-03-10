#!/bin/bash

# Next-Gen AI Tutoring System Deployment Script
# Version: 1.0.0

set -e  # Exit on error

echo "🚀 Next-Gen AI Tutoring System Deployment"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_DIR="backend"
FRONTEND_DIR="frontend"
VENV_DIR="venv"
REQUIREMENTS_FILE="requirements.txt"
API_PORT=8000

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    echo "🔍 Checking prerequisites..."
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_status "Python $PYTHON_VERSION found"
    else
        print_error "Python 3 not found. Please install Python 3.9 or higher."
        exit 1
    fi
    
    # Check pip
    if command -v pip3 &> /dev/null; then
        print_status "pip3 found"
    else
        print_warning "pip3 not found. Attempting to install..."
        sudo apt-get install python3-pip -y || sudo yum install python3-pip -y
    fi
    
    # Check Node.js (optional for frontend)
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_status "Node.js $NODE_VERSION found"
    else
        print_warning "Node.js not found (optional for advanced frontend)"
    fi
}

# Setup virtual environment
setup_venv() {
    echo "🐍 Setting up Python virtual environment..."
    
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv $VENV_DIR
        print_status "Virtual environment created"
    else
        print_status "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source $VENV_DIR/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    print_status "pip upgraded"
}

# Install dependencies
install_dependencies() {
    echo "📦 Installing dependencies..."
    
    if [ -f "$BACKEND_DIR/$REQUIREMENTS_FILE" ]; then
        pip install -r $BACKEND_DIR/$REQUIREMENTS_FILE
        print_status "Backend dependencies installed"
    else
        print_error "Requirements file not found: $BACKEND_DIR/$REQUIREMENTS_FILE"
        exit 1
    fi
    
    # Install development dependencies
    pip install pytest pytest-asyncio black flake8
    print_status "Development dependencies installed"
}

# Initialize database
init_database() {
    echo "🗄️ Initializing database..."
    
    # Create data directory
    mkdir -p data
    print_status "Data directory created"
    
    # Initialize sample data
    if [ -f "$BACKEND_DIR/main.py" ]; then
        cd $BACKEND_DIR
        python -c "
from main import initialize_sample_data
initialize_sample_data()
print('Sample data initialized')
        "
        cd ..
        print_status "Sample data loaded"
    else
        print_warning "Could not initialize sample data"
    fi
}

# Run tests
run_tests() {
    echo "🧪 Running tests..."
    
    if [ -d "$BACKEND_DIR" ]; then
        cd $BACKEND_DIR
        
        # Run unit tests if they exist
        if [ -d "tests" ]; then
            python -m pytest tests/ -v
        else
            print_warning "No tests directory found. Skipping tests."
        fi
        
        cd ..
    fi
}

# Start backend server
start_backend() {
    echo "🚀 Starting backend server..."
    
    if [ -f "$BACKEND_DIR/main.py" ]; then
        cd $BACKEND_DIR
        
        # Check if port is available
        if lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null ; then
            print_warning "Port $API_PORT is already in use"
            read -p "Use a different port? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                read -p "Enter port number: " API_PORT
            fi
        fi
        
        # Start server in background
        nohup python main.py > server.log 2>&1 &
        SERVER_PID=$!
        
        # Wait for server to start
        sleep 3
        
        # Check if server is running
        if curl -s http://localhost:$API_PORT > /dev/null; then
            print_status "Backend server started on port $API_PORT"
            echo "📝 Server logs: $BACKEND_DIR/server.log"
            echo "🔗 API URL: http://localhost:$API_PORT"
            echo "📚 API Documentation: http://localhost:$API_PORT/docs"
        else
            print_error "Failed to start backend server"
            cat server.log
            exit 1
        fi
        
        cd ..
    else
        print_error "Backend main.py not found"
        exit 1
    fi
}

# Start frontend (simple HTTP server)
start_frontend() {
    echo "🌐 Starting frontend..."
    
    if [ -f "$FRONTEND_DIR/demo.html" ]; then
        # Check if Python HTTP server is available
        if command -v python3 &> /dev/null; then
            cd $FRONTEND_DIR
            
            # Find an available port
            FRONTEND_PORT=8080
            while lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t >/dev/null ; do
                FRONTEND_PORT=$((FRONTEND_PORT + 1))
            done
            
            # Start HTTP server in background
            nohup python3 -m http.server $FRONTEND_PORT > frontend.log 2>&1 &
            FRONTEND_PID=$!
            
            sleep 2
            
            print_status "Frontend server started on port $FRONTEND_PORT"
            echo "🔗 Frontend URL: http://localhost:$FRONTEND_PORT/demo.html"
            echo "📝 Frontend logs: $FRONTEND_DIR/frontend.log"
            
            cd ..
        else
            print_warning "Python not available for HTTP server"
            print_status "You can open frontend/demo.html directly in your browser"
        fi
    else
        print_warning "Frontend demo not found"
    fi
}

# Display deployment info
display_info() {
    echo ""
    echo "🎉 Deployment Complete!"
    echo "======================"
    echo ""
    echo "📊 System Status:"
    echo "   Backend API:  http://localhost:$API_PORT"
    echo "   API Docs:     http://localhost:$API_PORT/docs"
    
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "   Frontend:     http://localhost:$FRONTEND_PORT/demo.html"
    else
        echo "   Frontend:     Open frontend/demo.html in browser"
    fi
    
    echo ""
    echo "🔧 Management Commands:"
    echo "   View backend logs:  tail -f $BACKEND_DIR/server.log"
    echo "   Stop backend:       kill $SERVER_PID"
    
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "   View frontend logs: tail -f $FRONTEND_DIR/frontend.log"
        echo "   Stop frontend:      kill $FRONTEND_PID"
    fi
    
    echo ""
    echo "🧪 Test the system:"
    echo "   curl http://localhost:$API_PORT"
    echo "   curl -X POST http://localhost:$API_PORT/api/system/status"
    echo ""
    echo "📚 Next steps:"
    echo "   1. Open the frontend URL in your browser"
    echo "   2. Try submitting interactions"
    echo "   3. Check the API documentation for integration"
    echo ""
}

# Cleanup function
cleanup() {
    echo ""
    print_warning "Cleaning up..."
    
    # Kill background processes
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null || true
        print_status "Backend server stopped"
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        print_status "Frontend server stopped"
    fi
    
    # Deactivate virtual environment
    deactivate 2>/dev/null || true
}

# Main deployment process
main() {
    echo "Next-Gen AI Tutoring System Deployment"
    echo "======================================"
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Run deployment steps
    check_prerequisites
    setup_venv
    install_dependencies
    init_database
    run_tests
    start_backend
    start_frontend
    display_info
    
    # Keep script running
    echo ""
    print_warning "Press Ctrl+C to stop all servers and exit"
    wait
}

# Run main function
main "$@"