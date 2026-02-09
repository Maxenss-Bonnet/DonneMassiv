import pika
import time

def connect():
    for i in range(5):
        try:
            return pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
        except:
            print("Retrying connection to RabbitMQ...")
            time.sleep(2)
    raise Exception("Could not connect to RabbitMQ")

connection = connect()
channel = connection.channel()
channel.queue_declare(queue='task_queue', durable=True)

for i in range(100):
    msg = f"Task #{i}"
    channel.basic_publish(
        exchange='',
        routing_key='task_queue',
        body=msg,
        properties=pika.BasicProperties(delivery_mode=2)
    )
    print(f"📤 Sent: {msg}")
    time.sleep(1)

connection.close()
