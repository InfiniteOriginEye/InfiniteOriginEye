# =============================================================================
# SC&C Makefile - Development Commands
# =============================================================================

.PHONY: help dev dev-infra dev-backend dev-frontend stop test lint clean \
        docker-up docker-down docker-logs seed simulate \
        proto-gen migrate db-reset

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---- Development ----

dev: ## Start full dev environment (infra + backend + frontend)
	docker compose up -d postgres redis kafka zookeeper emqx minio
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@echo "Starting backend services..."
	$(MAKE) dev-backend

dev-infra: ## Start only infrastructure (DB, Kafka, Redis, MQTT, MinIO)
	docker compose up -d postgres redis kafka zookeeper emqx minio

dev-backend: ## Start all FastAPI backend services
	@echo "S1 (8001) | S2 (8002) | S4 (8004) | S5 (8005) | S6 (8006) | S7 (8007)"
	uvicorn services.s1-incident-intake.app.main:app --port 8001 --reload &
	uvicorn services.s2-review-dashboard.app.main:app --port 8002 --reload &
	uvicorn services.s4-rescue-coord.app.main:app --port 8004 --reload &
	uvicorn services.s5-early-warning.app.main:app --port 8005 --reload &
	uvicorn services.s6-erss-connector.app.main:app --port 8006 --reload &
	uvicorn services.s7-data-handover.app.main:app --port 8007 --reload

dev-s3: ## Start S3 Go gRPC server
	cd services/s3-swarm-command && go run cmd/server/main.go

dev-frontend: ## Start frontend dev servers
	cd frontend/s2-dashboard && npm run dev &
	cd frontend/s3-tactical && npm run dev

stop: ## Stop all services
	docker compose down
	pkill -f uvicorn || true

# ---- Docker ----

docker-up: ## Start all Docker services (including monitoring)
	docker compose --profile monitoring --profile ml up -d

docker-down: ## Stop and remove all containers
	docker compose --profile monitoring --profile ml down -v

docker-logs: ## Tail all container logs
	docker compose logs -f

# ---- Database ----

migrate: ## Run Alembic migrations for all services
	@for svc in s1-incident-intake s2-review-dashboard s4-rescue-coord s5-early-warning s6-erss-connector s7-data-handover; do \
		echo "Migrating $$svc..."; \
		cd services/$$svc && alembic upgrade head && cd ../..; \
	done

db-reset: ## Reset database (WARNING: destroys all data)
	docker compose down -v
	docker compose up -d postgres
	@sleep 5
	$(MAKE) migrate

seed: ## Seed database with reference data and test incidents
	python scripts/seed/seed_all.py

# ---- Simulation ----

simulate: ## Start drone + ERSS simulators
	@echo "Starting drone simulator..."
	python drone-sim/mother-drone/simulator.py &
	@echo "Starting ERSS incident generator..."
	python simulators/erss-inbound/scripts/generate.py &

# ---- Protocol Buffers ----

proto-gen: ## Generate Go + Python + TS code from .proto files
	protoc --go_out=. --go-grpc_out=. services/s3-swarm-command/api/proto/swarm/v1/swarm.proto
	protoc --python_out=. services/s3-swarm-command/api/proto/swarm/v1/swarm.proto

# ---- Testing ----

test: ## Run all tests
	@for svc in s1-incident-intake s2-review-dashboard s4-rescue-coord s5-early-warning s6-erss-connector s7-data-handover; do \
		echo "Testing $$svc..."; \
		cd services/$$svc && pytest && cd ../..; \
	done
	cd services/s3-swarm-command && go test ./... && cd ../..
	cd frontend/s2-dashboard && npm test && cd ../..
	cd frontend/s3-tactical && npm test && cd ../..

lint: ## Lint all code
	@for svc in s1-incident-intake s2-review-dashboard s4-rescue-coord s5-early-warning s6-erss-connector s7-data-handover; do \
		cd services/$$svc && ruff check . && cd ../..; \
	done
	cd services/s3-swarm-command && golangci-lint run && cd ../..

# ---- Cleanup ----

clean: ## Remove all generated files and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null || true
	rm -rf .ruff_cache .mypy_cache
