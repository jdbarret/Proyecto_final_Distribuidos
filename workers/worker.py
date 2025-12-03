"""
Worker service for processing prime number generation requests
Consumes messages from RabbitMQ and generates prime numbers
"""
import pika
import json
import logging
import time
import signal
import sys

from config import RABBITMQ_URL, RABBITMQ_QUEUE, WORKER_ID, PREFETCH_COUNT
import database as db
from prime_utils import generate_prime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_flag = False


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_flag
    logger.info(f"Received shutdown signal {sig}. Finishing current task...")
    shutdown_flag = True


def process_message(ch, method, properties, body):
    """Process a single message from the queue"""
    try:
        message = json.loads(body)
        request_id = message['request_id']
        digits = message['digits']
        index = message['index']
        total = message['total']
        
        logger.info(f"[{WORKER_ID}] Processing request {request_id} ({index}/{total}) - generating {digits}-digit prime")
        
        # Generate prime number
        start_time = time.time()
        prime = generate_prime(digits)
        generation_time = time.time() - start_time
        
        logger.info(f"[{WORKER_ID}] Generated prime in {generation_time:.2f}s: {str(prime)[:20]}...")
        
        # Store in database (with conflict handling for uniqueness)
        max_retries = 10
        retry_count = 0
        
        while retry_count < max_retries:
            success = db.add_prime_number(request_id, prime)
            
            if success:
                logger.info(f"[{WORKER_ID}] Stored prime for request {request_id} ({index}/{total})")
                break
            else:
                # Prime already exists, generate a new one
                logger.warning(f"[{WORKER_ID}] Duplicate prime detected, regenerating...")
                prime = generate_prime(digits)
                retry_count += 1
        
        if retry_count >= max_retries:
            logger.error(f"[{WORKER_ID}] Failed to generate unique prime after {max_retries} attempts")
            # Reject without requeue to prevent infinite loops
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        
        # Acknowledge message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"[{WORKER_ID}] Successfully completed request {request_id} ({index}/{total})")
        
    except Exception as e:
        logger.error(f"[{WORKER_ID}] Error processing message: {e}")
        # Reject message and requeue for retry
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    """Main worker loop"""
    global shutdown_flag
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info(f"[{WORKER_ID}] Starting worker...")
    
    # Initialize database connection pool
    try:
        db.init_db_pool()
        logger.info(f"[{WORKER_ID}] Database connection pool initialized")
    except Exception as e:
        logger.error(f"[{WORKER_ID}] Failed to initialize database: {e}")
        sys.exit(1)
    
    # Connect to RabbitMQ with retry logic
    max_retries = 10
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            
            # Declare queue (idempotent)
            channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            
            # Set prefetch count for fair dispatch
            channel.basic_qos(prefetch_count=PREFETCH_COUNT)
            
            logger.info(f"[{WORKER_ID}] Connected to RabbitMQ, waiting for messages...")
            
            # Set up consumer
            channel.basic_consume(
                queue=RABBITMQ_QUEUE,
                on_message_callback=process_message,
                auto_ack=False
            )
            
            # Start consuming
            while not shutdown_flag:
                connection.process_data_events(time_limit=1)
            
            # Graceful shutdown
            logger.info(f"[{WORKER_ID}] Shutting down gracefully...")
            channel.stop_consuming()
            connection.close()
            db.close_db_pool()
            logger.info(f"[{WORKER_ID}] Worker stopped")
            sys.exit(0)
            
        except pika.exceptions.AMQPConnectionError as e:
            if attempt < max_retries - 1:
                logger.warning(f"[{WORKER_ID}] Failed to connect to RabbitMQ (attempt {attempt + 1}/{max_retries}): {e}")
                logger.info(f"[{WORKER_ID}] Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"[{WORKER_ID}] Failed to connect to RabbitMQ after {max_retries} attempts")
                sys.exit(1)
        except Exception as e:
            logger.error(f"[{WORKER_ID}] Unexpected error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
