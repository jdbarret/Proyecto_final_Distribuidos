# Proyecto final Sistemas Distribuidos - Generador de numeros primos 

# Nombres - Códigos
Laura Vanessa Hernández García - 160004630
Jose Daniel Barreto Aguilera - 160004622

# Instrucciones de uso y despliegue

Para desplegar el generador de numeros primos, primero ingresar a:
https://killercoda.com/playgrounds/scenario/kubernetes   
(Se requiere inicio de sesión)

Se abrirá una terminal de comandos, donde inicialmente se obtendrá el repositorio del proyecto

# Ejecutar el siguiente comando
git clone https://github.com/jdbarret/Proyecto_final_Distribuidos.git 

# Dirigirse al directorio
cd Proyecto_final_Distribuidos

# Ahora se ejecutan una serie de comandos, que para mayor facilidad se ejecutan en un script

chmod +x script-arranque.sh

./script-arranque.sh

Verificar que todos digan running y estamos listo para probar el sistema.

Esperar 100 segundos y ejecutar el siguiente comando, para verificar que todos tengas 
status: "Running"

kubectl get all -n prime-system


# Para probar el sistema debemos hacer peticiones a la api

# Crear un request
Para crear un request es necesario crear la siguiente petición donde podemos definir la cantidad de números primos
a generar y los dígitos que deseamos en cada número

RESPONSE=$(curl -s -X POST http://localhost:30080/api/new \
  -H "Content-Type: application/json" \
  -d '{"quantity": 5, "digits": 12}')

Luego al enviar esta petición se creará un request_id.

Para extraerlo

REQUEST_ID=$(echo $RESPONSE | grep -o '"request_id":"[^"]*"' | cut -d'"' -f4)

echo "Request ID: $REQUEST_ID"

Se obtendrá una salida como esta, la cual usaremos para request_id para las siguientes peticiones:
a7dcb850-c522-40bd-93c9-4536a39fca08

curl http://localhost:30080/api/status/{request_id}

Luego ya podremos ver los resultados del generador de números primos, donde también especifiquemos el request_id.

curl http://localhost:30080/api/result/{request_id}

Al ejecutar este comando, en la consola se mostrarán los números primos que han sido solicitados en la petición inicial,
este es un ejemplo de visualización si todo fue exitoso:
{"request_id":"a7dcb850-c522-40bd-93c9-4536a39fca08","quantity":5,"generated_count":5,"status":"completed",
"prime_numbers":["913060254787","101171971781","156908175719","623459046827","356057906851"]}











## 🏗️ Arquitectura

```
┌─────────────────┐
│ Microservicios  │ ──┐
│   (FastAPI)     │   │
└─────────────────┘   │
                      ▼
              ┌──────────────┐
              │  RabbitMQ    │
              │ (Cola Msgs)  │
              └──────────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │Worker 1│  │Worker 2│  │Worker 3│
    └────────┘  └────────┘  └────────┘
         │            │            │
         └────────────┼────────────┘
                      ▼
              ┌──────────────┐
              │  PostgreSQL  │
              │     (DB)     │
              └──────────────┘
```

## ✨ Características

- ✅ Generación de números primos grandes (12+ dígitos)
- ✅ Algoritmo Miller-Rabin con garantía 100% de primalidad
- ✅ Procesamiento distribuido con múltiples workers
- ✅ Sin duplicados en la misma solicitud
- ✅ API REST con 3 endpoints principales
- ✅ Escalable horizontalmente con Kubernetes
- ✅ Comunicación asíncrona mediante colas

## 🚀 API Endpoints

### 1. **New** - Crear solicitud de generación
```bash
POST /api/new
```
**Body:**
```json
{
  "quantity": 10,
  "digits": 12
}
```
**Respuesta:**
```json
{
  "request_id": "uuid-de-solicitud",
  "message": "Request created successfully..."
}
```

### 2. **Status** - Consultar estado de solicitud
```bash
GET /api/status/{request_id}
```
**Respuesta:**
```json
{
  "request_id": "uuid-de-solicitud",
  "quantity": 10,
  "generated_count": 7,
  "status": "pending",
  "progress_percentage": 70.0
}
```

### 3. **Result** - Obtener números primos generados
```bash
GET /api/result/{request_id}
```
**Respuesta:**
```json
{
  "request_id": "uuid-de-solicitud",
  "quantity": 10,
  "generated_count": 10,
  "status": "completed",
  "prime_numbers": [
    "123456789101",
    "987654321019",
    ...
  ]
}
```

## 📦 Componentes

### Microservicios
- **Lenguaje**: Python 3.11
- **Framework**: FastAPI
- **Funciones**:
  - Recibir solicitudes HTTP
  - Validar parámetros
  - Publicar mensajes en la cola
  - Consultar estado y resultados

### Workers
- **Lenguaje**: Python 3.11
- **Funciones**:
  - Consumir mensajes de RabbitMQ
  - Generar números primos
  - Almacenar en base de datos
  - Evitar duplicados

### Base de Datos
- **Motor**: PostgreSQL 15
- **Tablas**:
  - `requests`: Solicitudes de generación
  - `prime_numbers`: Números primos generados
- **Características**:
  - Constraint UNIQUE para evitar duplicados
  - Índices para consultas rápidas

### Cola de Mensajes
- **Sistema**: RabbitMQ 3.12
- **Configuración**:
  - Cola durable
  - Mensajes persistentes
  - Fair dispatch entre workers

## 🛠️ Instalación y Despliegue

### Prerrequisitos
- Docker & Docker Compose
- Kubernetes (minikube, k3s, o cluster cloud)
- kubectl configurado

### Opción 1: Docker Compose (Desarrollo Local)

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd Proyecto_final_Distribuidos
```

2. **Construir y levantar servicios**
```bash
docker-compose up --build
```

3. **Verificar servicios**
- API: http://localhost:8000
- RabbitMQ Management: http://localhost:15672 (guest/guest)
- PostgreSQL: localhost:5432

4. **Probar la API**
```bash
# Crear solicitud
curl -X POST http://localhost:8000/api/new \
  -H "Content-Type: application/json" \
  -d '{"quantity": 5, "digits": 12}'

# Verificar estado
curl http://localhost:8000/api/status/{request_id}

# Obtener resultados
curl http://localhost:8000/api/result/{request_id}
```

### Opción 2: Kubernetes (Producción)

1. **Construir y publicar imágenes Docker**
```bash
# Microservicios
cd microservices
docker build -t your-registry/prime-microservices:latest .
docker push your-registry/prime-microservices:latest

# Workers
cd ../workers
docker build -t your-registry/prime-worker:latest .
docker push your-registry/prime-worker:latest
```

2. **Actualizar manifiestos**
Editar `k8s/microservices.yaml` y `k8s/workers.yaml` para usar tus imágenes.

3. **Desplegar en Kubernetes**
```bash
# Crear namespace
kubectl apply -f k8s/namespace.yaml

# Desplegar configuración
kubectl apply -f k8s/config.yaml

# Desplegar base de datos
kubectl apply -f k8s/postgres.yaml

# Desplegar RabbitMQ
kubectl apply -f k8s/rabbitmq.yaml

# Esperar a que estén listos
kubectl wait --for=condition=ready pod -l app=postgres -n prime-system --timeout=120s
kubectl wait --for=condition=ready pod -l app=rabbitmq -n prime-system --timeout=120s

# Desplegar microservicios
kubectl apply -f k8s/microservices.yaml

# Desplegar workers
kubectl apply -f k8s/workers.yaml
```

4. **Verificar despliegue**
```bash
kubectl get pods -n prime-system
kubectl get services -n prime-system
```

5. **Acceder a la API**
```bash
# Obtener la IP externa
kubectl get service microservices -n prime-system

# O usar port-forward para testing
kubectl port-forward -n prime-system service/microservices 8000:8000
```

6. **Escalar workers**
```bash
kubectl scale deployment workers --replicas=5 -n prime-system
```

## 🧪 Pruebas

### Prueba básica
```bash
# 1. Crear solicitud de 3 primos de 12 dígitos
REQUEST_ID=$(curl -s -X POST http://localhost:8000/api/new \
  -H "Content-Type: application/json" \
  -d '{"quantity": 3, "digits": 12}' | jq -r '.request_id')

echo "Request ID: $REQUEST_ID"

# 2. Monitorear progreso
while true; do
  curl -s http://localhost:8000/api/status/$REQUEST_ID | jq
  sleep 2
done

# 3. Obtener resultados
curl -s http://localhost:8000/api/result/$REQUEST_ID | jq
```

### Prueba de carga
```bash
# Generar múltiples solicitudes
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/new \
    -H "Content-Type: application/json" \
    -d '{"quantity": 5, "digits": 12}'
  sleep 1
done
```

## 🔍 Algoritmo de Primalidad

El sistema utiliza el **test de Miller-Rabin** con 40 rondas, garantizando:
- Probabilidad de error < 2^-80 (prácticamente 0)
- Eficiencia para números grandes (12+ dígitos)
- Verificación adicional con división por primos pequeños

```python
def is_prime_miller_rabin(n, k=40):
    # Implementación determinística
    # k=40 rondas garantiza primalidad 100%
```

## 📊 Monitoreo

### Logs de servicios (Docker Compose)
```bash
docker-compose logs -f microservices
docker-compose logs -f worker1
```

### Logs de pods (Kubernetes)
```bash
kubectl logs -f -n prime-system -l app=microservices
kubectl logs -f -n prime-system -l app=worker
```

### RabbitMQ Management
- URL: http://localhost:15672
- Usuario: guest
- Password: guest

### Métricas de base de datos
```bash
# Conectar a PostgreSQL
docker exec -it primes-postgres psql -U postgres -d primes_db

# Consultas útiles
SELECT COUNT(*) FROM requests;
SELECT COUNT(*) FROM prime_numbers;
SELECT r.id, r.quantity, COUNT(p.id) as generated 
FROM requests r 
LEFT JOIN prime_numbers p ON r.id = p.request_id 
GROUP BY r.id, r.quantity;
```

## 🔒 Seguridad

- Validación de entrada en API
- Secrets separados en Kubernetes
- Conexiones de base de datos con pooling
- Mensajes persistentes en RabbitMQ
- Constraint UNIQUE para evitar duplicados

## 📝 Estructura del Proyecto

```
.
├── microservices/
│   ├── main.py              # API FastAPI
│   ├── config.py            # Configuración
│   ├── database.py          # Operaciones DB
│   ├── prime_utils.py       # Algoritmo de primos
│   ├── requirements.txt     # Dependencias Python
│   └── Dockerfile           # Imagen Docker
├── workers/
│   ├── worker.py            # Worker principal
│   ├── config.py            # Configuración
│   ├── database.py          # Operaciones DB
│   ├── prime_utils.py       # Algoritmo de primos
│   ├── requirements.txt     # Dependencias Python
│   └── Dockerfile           # Imagen Docker
├── database/
│   └── schema.sql           # Schema PostgreSQL
├── k8s/
│   ├── namespace.yaml       # Namespace
│   ├── config.yaml          # ConfigMaps y Secrets
│   ├── postgres.yaml        # Despliegue PostgreSQL
│   ├── rabbitmq.yaml        # Despliegue RabbitMQ
│   ├── microservices.yaml   # Despliegue API
│   └── workers.yaml         # Despliegue Workers
├── docker-compose.yml       # Orquestación local
└── README.md               # Este archivo
```

## 🐛 Solución de Problemas

### Los workers no se conectan a RabbitMQ
```bash
# Verificar que RabbitMQ esté corriendo
kubectl get pods -n prime-system -l app=rabbitmq

# Revisar logs
kubectl logs -n prime-system -l app=rabbitmq
```

### Error de conexión a base de datos
```bash
# Verificar que PostgreSQL esté listo
kubectl get pods -n prime-system -l app=postgres

# Probar conexión
kubectl exec -it -n prime-system <postgres-pod> -- psql -U postgres -d primes_db
```

### La generación es muy lenta
```bash
# Escalar workers
kubectl scale deployment workers --replicas=10 -n prime-system

# O ajustar PREFETCH_COUNT en config.yaml
```

## 📄 Licencia

Este proyecto es parte de un trabajo final de sistemas distribuidos.

## 👥 Autor

Desarrollado como proyecto final de Sistemas Distribuidos.