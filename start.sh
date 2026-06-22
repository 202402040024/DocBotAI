#!/bin/sh
set -e

BACKEND_PORT="8001"
FRONTEND_PORT="${PORT:-8000}"

echo "==> Starting FastAPI backend on internal :${BACKEND_PORT}..."
uvicorn server.main:app --host 0.0.0.0 --port "${BACKEND_PORT}" &
BACKEND_PID=$!

echo "==> Waiting for backend to be ready..."
sleep 3

echo "==> Starting Streamlit frontend on :${FRONTEND_PORT}..."
export API_BACKEND_URL="http://localhost:${BACKEND_PORT}"

streamlit run streamlit_app/app.py \
    --server.port "${FRONTEND_PORT}" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false &
FRONTEND_PID=$!

trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGTERM SIGINT

wait $FRONTEND_PID
