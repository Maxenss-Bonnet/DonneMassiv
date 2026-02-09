import pika
import time

# Function to handle connection retries
def connect():
    for i in range(5):
        try:
            print("📦 Connecting to RabbitMQ...")
            return pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
        except Exception as e:
            print(f"⚠️ Connection failed, retrying... {e}")
            time.sleep(2)
    raise Exception("Could not connect to RabbitMQ")

# Function to handle message processing
def callback(ch, method, properties, body):
    msg = body.decode()  # Decode the message from bytes to string
    try:
        print(f"📥 Received: {msg}")

        # Simulate a delay to represent processing time
        time.sleep(2)
        
        # Simulate task processing
        print(f"✅ Processed: {msg}")

        # Acknowledge that the message has been processed
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"🔏 Message acknowledged: {msg}")

    except Exception as e:
        print(f"⚠️ Error processing message: {e}")
        # Acknowledge even in case of error to prevent message blocking
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"🔏 Message acknowledged due to error: {msg}")

# Main logic for consuming messages
try:
    connection = connect()  # Establish connection to RabbitMQ
    channel = connection.channel()  # Create a channel

    # Declare the queue with durable=True (so it survives RabbitMQ restart)
    channel.queue_declare(queue='task_queue', durable=True)

    # Ensure one message is processed at a time (QOS - Quality of Service)
    channel.basic_qos(prefetch_count=1)

    # Set up the consumer, defining the callback function
    channel.basic_consume(queue='task_queue', on_message_callback=callback, auto_ack=False)

    print("👂 Waiting for messages... To exit, press CTRL+C")

    # Start consuming messages (this will block until interrupted)
    channel.start_consuming()

except KeyboardInterrupt:
    print("👋 Interrupted by user, closing connection...")
    connection.close()

except Exception as e:
    print(f"❌ Error occurred: {e}")
