#!/bin/bash


set -e

echo "=== Desplegando en Kubernetes ==="
echo ""

# 1. Namespace
echo "[1/8] Creando namespace..."
kubectl apply -f k8s/namespace.yaml

# 2. Config
echo "[2/8] Aplicando configuración..."
kubectl apply -f k8s/config.yaml

# 3. PostgreSQL
echo "[3/8] Desplegando PostgreSQL..."
kubectl apply -f k8s/postgres.yaml

# 4. RabbitMQ
echo "[4/8] Desplegando RabbitMQ..."
kubectl apply -f k8s/rabbitmq.yaml

# 5.  Esperar Postgres
echo "[5/8] Esperando PostgreSQL..."
kubectl wait --for=condition=ready pod -l app=postgres -n prime-system --timeout=120s

# 6. Esperar RabbitMQ
echo "[6/8] Esperando RabbitMQ..."
kubectl wait --for=condition=ready pod -l app=rabbitmq -n prime-system --timeout=120s

# 7. Microservices
echo "[7/8] Desplegando microservicios..."
kubectl apply -f k8s/microservices.yaml

# 8. Workers
echo "[8/8] Desplegando workers..."
kubectl apply -f k8s/workers.yaml

echo ""
echo "Despliegue completado!"
echo ""
echo "Verificar estado:"
kubectl get all -n prime-system

echo "Si alguno no dice running: corraaan!!"

echo ""


