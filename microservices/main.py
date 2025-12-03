"""
FastAPI Microservice for Prime Number Generation System
Provides three endpoints: New, Status, and Result
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
import pika
import json
import logging
from typing import List, Dict, Any
import uuid

from config import RABBITMQ_URL, RABBITMQ_QUEUE, API_HOST, API_PORT
import database as db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    try:
        db.init_db_pool()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
    yield
    
    # Shutdown
    db.close_db_pool()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Prime Number Generation Microservice",
    description="API for requesting and retrieving prime number generation",
    version="1.0.0",
    lifespan=lifespan
)


# Pydantic models
class NewRequest(BaseModel):
    quantity: int = Field(..., gt=0, description="Number of prime numbers to generate")
    digits: int = Field(..., ge=12, description="Number of digits in each prime (minimum 12)")


class NewResponse(BaseModel):
    request_id: str
    message: str


class StatusResponse(BaseModel):
    request_id: str
    quantity: int
    generated_count: int
    status: str
    progress_percentage: float


class PrimeNumber(BaseModel):
    value: str
    created_at: str


class ResultResponse(BaseModel):
    request_id: str
    quantity: int
    generated_count: int
    status: str
    prime_numbers: List[str]


def send_to_queue(request_id: str, quantity: int, digits: int):
    """Send a request to RabbitMQ queue"""
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        
        # Declare queue (idempotent)
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
        
        # Send individual messages for each prime to generate
        for i in range(quantity):
            message = {
                'request_id': request_id,
                'digits': digits,
                'index': i + 1,
                'total': quantity
            }
            
            channel.basic_publish(
                exchange='',
                routing_key=RABBITMQ_QUEUE,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                )
            )
        
        connection.close()
        logger.info(f"Sent {quantity} messages to queue for request {request_id}")
    except Exception as e:
        logger.error(f"Error sending to queue: {e}")
        raise


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Prime Number Generation Microservice"}


@app.post("/api/new", response_model=NewResponse)
async def new_request(request: NewRequest):
    """
    Create a new prime number generation request
    
    - **quantity**: Number of prime numbers to generate
    - **digits**: Number of digits for each prime number (minimum 12)
    """
    try:
        # Create request in database
        db_request = db.create_request(request.quantity, request.digits)
        request_id = str(db_request['id'])
        
        # Send messages to queue
        send_to_queue(request_id, request.quantity, request.digits)
        
        logger.info(f"Created new request {request_id} for {request.quantity} primes with {request.digits} digits")
        
        return NewResponse(
            request_id=request_id,
            message=f"Request created successfully. Generating {request.quantity} prime numbers with {request.digits} digits."
        )
    except Exception as e:
        logger.error(f"Error creating new request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{request_id}", response_model=StatusResponse)
async def get_status(request_id: str):
    """
    Get the status of a prime generation request
    
    - **request_id**: The UUID of the request
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(request_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request_id format")
        
        status_data = db.get_request_status(request_id)
        
        if not status_data:
            raise HTTPException(status_code=404, detail="Request not found")
        
        quantity = status_data['quantity']
        generated_count = status_data['generated_count']
        progress = (generated_count / quantity * 100) if quantity > 0 else 0
        
        # Update status if complete
        if generated_count >= quantity and status_data['status'] != 'completed':
            db.update_request_status(request_id, 'completed')
            status_data['status'] = 'completed'
        
        return StatusResponse(
            request_id=request_id,
            quantity=quantity,
            generated_count=generated_count,
            status=status_data['status'],
            progress_percentage=round(progress, 2)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status for request {request_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/result/{request_id}", response_model=ResultResponse)
async def get_result(request_id: str):
    """
    Get the generated prime numbers for a request
    
    - **request_id**: The UUID of the request
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(request_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request_id format")
        
        status_data = db.get_request_status(request_id)
        
        if not status_data:
            raise HTTPException(status_code=404, detail="Request not found")
        
        prime_numbers = db.get_request_results(request_id)
        
        return ResultResponse(
            request_id=request_id,
            quantity=status_data['quantity'],
            generated_count=status_data['generated_count'],
            status=status_data['status'],
            prime_numbers=[p['prime_value'] for p in prime_numbers]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting results for request {request_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
