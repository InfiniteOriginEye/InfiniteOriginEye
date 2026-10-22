/*
Telemetry Ingest Service — Swarm Command & Control

Receives drone telemetry via MQTT, processes it,
and publishes to Kafka for downstream consumers.

Usage:
  go run ./cmd/telemetry-ingest
*/
package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/scc-project/telemetry-ingest/internal/consumer"
	"github.com/scc-project/telemetry-ingest/internal/processor"
	"github.com/scc-project/telemetry-ingest/internal/publisher"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// ── Configuration ─────────────────────────────────────
	mqttBroker := envOr("MQTT_BROKER", "tcp://localhost:1883")
	kafkaBrokers := envOr("KAFKA_BROKERS", "localhost:9092")
	redisURL := envOr("REDIS_URL", "redis://localhost:6379/0")

	log.Printf("Starting telemetry-ingest service")
	log.Printf("  MQTT broker:  %s", mqttBroker)
	log.Printf("  Kafka brokers: %s", kafkaBrokers)
	log.Printf("  Redis URL:    %s", redisURL)

	// ── Initialise components ─────────────────────────────
	mqttConsumer, err := consumer.NewMQTTConsumer(mqttBroker)
	if err != nil {
		log.Fatalf("Failed to create MQTT consumer: %v", err)
	}

	kafkaPublisher, err := publisher.NewKafkaPublisher(kafkaBrokers)
	if err != nil {
		log.Fatalf("Failed to create Kafka publisher: %v", err)
	}

	proc := processor.NewTelemetryProcessor(kafkaPublisher)

	// ── Start consuming ───────────────────────────────────
	go func() {
		if err := mqttConsumer.Start(ctx, proc); err != nil {
			log.Printf("MQTT consumer stopped: %v", err)
			cancel()
		}
	}()

	log.Printf("Telemetry ingest service is running")

	// ── Graceful shutdown ─────────────────────────────────
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	select {
	case <-sigCh:
		log.Printf("Received shutdown signal")
	case <-ctx.Done():
		log.Printf("Context cancelled")
	}

	cancel()
	mqttConsumer.Close()
	kafkaPublisher.Close()
	log.Printf("Service shut down cleanly")
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
