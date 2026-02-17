# ── Stage 1: Build the React/Vite dashboard ─────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /build/dashboard

# Install dependencies first (better layer caching)
COPY dashboard/package.json dashboard/package-lock.json* ./
RUN npm ci --ignore-scripts 2>/dev/null || npm install

# Copy source and build
COPY dashboard/index.html dashboard/tsconfig.json dashboard/tsconfig.node.json ./
COPY dashboard/vite.config.ts dashboard/tailwind.config.js dashboard/postcss.config.js ./
COPY dashboard/src/ src/
RUN npm run build


# ── Stage 2: Production image ───────────────────────────────
FROM python:3.12-slim AS production

LABEL org.opencontainers.image.source="https://github.com/8ryanWh1t3/DeepSigma"
LABEL org.opencontainers.image.description="Σ OVERWATCH Dashboard — real-time monitoring for the DeepSigma agentic AI control plane"
LABEL org.opencontainers.image.licenses="MIT"

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx supervisor curl && \
        rm -rf /var/lib/apt/lists/*

        # Install Python dependencies for the API server
        RUN pip install --no-cache-dir \
            "fastapi>=0.104.0" \
                "uvicorn[standard]>=0.24.0" \
                    "jsonschema" \
                        "referencing>=0.35.0" \
                            "pyyaml>=6.0"

                            WORKDIR /app

                            # Copy built dashboard static files from stage 1
                            COPY --from=frontend-build /build/dashboard/dist /app/dashboard/dist

                            # Copy Python source for the API and DeepSigma package
                            COPY dashboard/server/ /app/dashboard/server/
                            COPY pyproject.toml setup.cfg* /app/
                            COPY engine/ /app/engine/
                            COPY coherence_ops/ /app/coherence_ops/
                            COPY verifiers/ /app/verifiers/
                            COPY tools/ /app/tools/
                            COPY specs/ /app/specs/
                            COPY adapters/ /app/adapters/

                            # Install DeepSigma package so coherence_ops is importable
                            RUN pip install --no-cache-dir -e /app 2>/dev/null || true

                            # ── nginx: serve static assets + reverse-proxy /api ─────────
                            RUN cat > /etc/nginx/sites-available/default <<'NGINX'
                            server {
                                listen 3000;
                                    server_name _;

                                        root /app/dashboard/dist;
                                            index index.html;

                                                # Serve dashboard SPA
                                                    location / {
                                                            try_files $uri $uri/ /index.html;
                                                                }

                                                                    # Proxy API calls to uvicorn
                                                                        location /api/ {
                                                                                proxy_pass http://127.0.0.1:8000;
                                                                                        proxy_set_header Host $host;
                                                                                                proxy_set_header X-Real-IP $remote_addr;
                                                                                                        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                                                                                                                proxy_set_header X-Forwarded-Proto $scheme;
                                                                                                                    }
                                                                                                                    
                                                                                                                        # Health check (proxied)
                                                                                                                            location /healthz {
                                                                                                                                    proxy_pass http://127.0.0.1:8000/api/health;
                                                                                                                                        }
                                                                                                                                        }
                                                                                                                                        NGINX
                                                                                                                                        
                                                                                                                                        # ── supervisord: run nginx + uvicorn as a single process ────
                                                                                                                                        RUN cat > /etc/supervisor/conf.d/overwatch.conf <<'SUPERVISOR'
                                                                                                                                        [supervisord]
                                                                                                                                        nodaemon=true
                                                                                                                                        logfile=/dev/stdout
                                                                                                                                        logfile_maxbytes=0
                                                                                                                                        
                                                                                                                                        [program:nginx]
                                                                                                                                        command=nginx -g "daemon off;"
                                                                                                                                        autostart=true
                                                                                                                                        autorestart=true
                                                                                                                                        stdout_logfile=/dev/stdout
                                                                                                                                        stdout_logfile_maxbytes=0
                                                                                                                                        stderr_logfile=/dev/stderr
                                                                                                                                        stderr_logfile_maxbytes=0
                                                                                                                                        
                                                                                                                                        [program:api]
                                                                                                                                        command=uvicorn dashboard.server.api:app --host 0.0.0.0 --port 8000 --workers 2
                                                                                                                                        directory=/app
                                                                                                                                        autostart=true
                                                                                                                                        autorestart=true
                                                                                                                                        stdout_logfile=/dev/stdout
                                                                                                                                        stdout_logfile_maxbytes=0
                                                                                                                                        stderr_logfile=/dev/stderr
                                                                                                                                        stderr_logfile_maxbytes=0
                                                                                                                                        SUPERVISOR
                                                                                                                                        
                                                                                                                                        # Data directory for episode/drift JSON files (mount volume here)
                                                                                                                                        RUN mkdir -p /app/data
                                                                                                                                        
                                                                                                                                        ENV PYTHONPATH=/app
                                                                                                                                        EXPOSE 3000
                                                                                                                                        
                                                                                                                                        HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
                                                                                                                                            CMD curl -f http://localhost:3000/healthz || exit 1
                                                                                                                                            
                                                                                                                                            CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
