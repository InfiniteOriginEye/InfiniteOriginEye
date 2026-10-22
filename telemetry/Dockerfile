FROM golang:1.22-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /telemetry-ingest ./cmd/telemetry-ingest

FROM alpine:3.20
COPY --from=builder /telemetry-ingest /usr/local/bin/telemetry-ingest
EXPOSE 9090 50051
CMD ["telemetry-ingest"]
