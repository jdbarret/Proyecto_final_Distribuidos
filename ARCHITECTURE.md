# Architecture Documentation

## System Overview

This is a cloud-native distributed system for generating large prime numbers using a microservices architecture with event-driven communication.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         KUBERNETES                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    Cloud Layer                        │  │
│  │                                                       │  │
│  │  ┌──────────────┐                                    │  │
│  │  │ Microservices│                                    │  │
│  │  │  (FastAPI)   │                                    │  │
│  │  │              │                                    │  │
│  │  │ - POST /new  │                                    │  │
│  │  │ - GET /status│                                    │  │
│  │  │ - GET /result│                                    │  │
│  │  └───────┬──────┘                                    │  │
│  │          │                                           │  │
│  │          ▼                                           │  │
│  │  ┌──────────────┐                                    │  │
│  │  │   RabbitMQ   │                                    │  │
│  │  │ Message Queue│                                    │  │
│  │  │  (durable)   │                                    │  │
│  │  └──────┬───────┘                                    │  │
│  │         │                                            │  │
│  │    ┌────┼────┬──────────────┐                       │  │
│  │    ▼    ▼    ▼              ▼                       │  │
│  │ ┌────┐┌────┐┌────┐     ┌────────┐                  │  │
│  │ │W#1 ││W#2 ││W#3 │ ... │ W#N    │                  │  │
│  │ │    ││    ││    │     │(scaled)│                  │  │
│  │ └─┬──┘└─┬──┘└─┬──┘     └───┬────┘                  │  │
│  │   │     │     │            │                        │  │
│  │   └─────┴─────┴────────────┘                        │  │
│  │              │                                       │  │
│  │              ▼                                       │  │
│  │      ┌──────────────┐                               │  │
│  │      │  PostgreSQL  │                               │  │
│  │      │   Database   │                               │  │
│  │      │              │                               │  │
│  │      │ - requests   │                               │  │
│  │      │ - primes     │                               │  │
│  │      └──────────────┘                               │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Microservices (FastAPI)
**Purpose**: REST API gateway for client requests

**Responsibilities**:
- Receive HTTP requests from clients
- Validate input parameters
- Create request records in database
- Publish messages to RabbitMQ queue
- Query and return status/results

**Technology**: 
- Python 3.11
- FastAPI framework
- Pydantic for validation
- psycopg2 for PostgreSQL
- pika for RabbitMQ

**Endpoints**:
1. `POST /api/new` - Create new prime generation request
2. `GET /api/status/{id}` - Get request status and progress
3. `GET /api/result/{id}` - Get generated prime numbers

### 2. Message Queue (RabbitMQ)
**Purpose**: Asynchronous communication and load distribution

**Responsibilities**:
- Store pending tasks
- Distribute work to available workers
- Ensure fair dispatch with prefetch_count=1
- Provide message persistence

**Configuration**:
- Queue: durable (survives broker restart)
- Messages: persistent (delivery_mode=2)
- Fair dispatch: workers take one message at a time

### 3. Workers
**Purpose**: Process prime generation tasks

**Responsibilities**:
- Consume messages from RabbitMQ
- Generate prime numbers using Miller-Rabin
- Store results in database
- Handle duplicate prevention
- Acknowledge/reject messages

**Algorithm**:
```python
Miller-Rabin with k=40 rounds:
  → Probability of error < 2^-80
  → Effectively 100% primality guarantee
  → Optimized with small prime pre-check
```

**Scalability**: 
- Horizontally scalable (Kubernetes Deployment)
- Independent workers
- No shared state except DB

### 4. Database (PostgreSQL)
**Purpose**: Persistent storage

**Schema**:
```sql
requests (
  id UUID PRIMARY KEY,
  quantity INTEGER,
  digits INTEGER,
  status VARCHAR(50),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)

prime_numbers (
  id SERIAL PRIMARY KEY,
  request_id UUID REFERENCES requests(id),
  prime_value TEXT,
  created_at TIMESTAMP,
  UNIQUE(request_id, prime_value)  -- Prevents duplicates
)
```

**Features**:
- UNIQUE constraint prevents duplicates
- Foreign key CASCADE delete
- Indexes for performance
- Connection pooling

## Data Flow

### Request Creation Flow
```
1. Client → POST /api/new {quantity: 10, digits: 12}
2. API validates input
3. API creates request in DB (status='pending')
4. API publishes 10 messages to RabbitMQ queue
5. API returns request_id to client
```

### Processing Flow
```
1. Worker consumes message from queue
2. Worker generates prime number
3. Worker attempts to store in DB
4. If duplicate → generate new prime, retry
5. If success → acknowledge message
6. If max retries → reject without requeue
```

### Status Query Flow
```
1. Client → GET /api/status/{id}
2. API queries DB: COUNT primes for request
3. Calculate progress: (generated/quantity) * 100
4. If complete → update status to 'completed'
5. Return status and progress
```

### Result Query Flow
```
1. Client → GET /api/result/{id}
2. API queries all primes for request_id
3. Return list of prime numbers
4. Client can verify primality independently
```

## Scalability

### Horizontal Scaling
- **Workers**: Scale up/down based on queue depth
  ```bash
  kubectl scale deployment workers --replicas=10
  ```
- **API**: Scale based on request rate
  ```bash
  kubectl scale deployment microservices --replicas=5
  ```

### Vertical Scaling
- PostgreSQL: Increase memory/CPU for larger datasets
- RabbitMQ: Increase memory for deeper queues

### Performance Optimization
- Database connection pooling
- Queue prefetch count tuning
- Worker concurrency adjustment
- Database indexes on frequently queried fields

## Reliability

### Message Durability
- Durable queue
- Persistent messages
- Manual acknowledgment
- Reject without requeue on permanent failures

### Database Consistency
- UNIQUE constraints
- Foreign key constraints
- Transaction support
- Automatic timestamp updates

### Error Handling
- Retry logic for transient failures
- Dead letter handling for permanent failures
- Graceful shutdown on SIGTERM
- Connection retry with backoff

## Security Considerations

### Network
- Services communicate within Kubernetes cluster
- LoadBalancer/Ingress for external access
- TLS can be added at ingress level

### Database
- Credentials in Kubernetes Secrets
- Connection pooling with limits
- Prepared statements (SQL injection prevention)

### Input Validation
- Pydantic models validate all inputs
- Minimum digits: 12
- Positive quantity required
- UUID validation for request IDs

## Monitoring

### Logs
```bash
# API logs
kubectl logs -f -l app=microservices -n prime-system

# Worker logs
kubectl logs -f -l app=worker -n prime-system
```

### Metrics
- Request completion rate
- Average generation time per digit count
- Queue depth
- Worker utilization
- Database connection pool usage

### Health Checks
- API: GET /
- PostgreSQL: pg_isready
- RabbitMQ: rabbitmq-diagnostics ping

## Deployment

### Local Development (Docker Compose)
```bash
docker compose up -d
```
- Suitable for testing and development
- All services on localhost
- PostgreSQL on port 5432
- RabbitMQ on ports 5672, 15672
- API on port 8000

### Production (Kubernetes)
```bash
kubectl apply -f k8s/
```
- Suitable for production workloads
- Horizontal auto-scaling
- Resource limits and requests
- Persistent volumes for database
- LoadBalancer for external access

## Future Enhancements

1. **Auto-scaling**: HPA based on queue depth
2. **Caching**: Redis for frequent status queries
3. **API Rate Limiting**: Prevent abuse
4. **Authentication**: OAuth2/JWT for API
5. **Monitoring**: Prometheus + Grafana
6. **Tracing**: OpenTelemetry for distributed tracing
7. **Dead Letter Queue**: Handle failed messages
8. **API Versioning**: Support multiple API versions
9. **Batch Processing**: Optimize for bulk requests
10. **Result Streaming**: WebSocket for real-time updates
