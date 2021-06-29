from kafka import KafkaProducer
from django.conf import settings



class ProducerServer(KafkaProducer):
	def publish_message(self, topic_name, key, value):
		try:
			key_bytes = bytes(key, encoding='utf-8') if key else None
			value_bytes = bytes(value, encoding='utf-8')
			self.send(topic_name, key=key_bytes, value=value_bytes)
			self.flush()
			print('Message published successfully.')
		except Exception as ex:
			print('Exception in publishing message')
			print(ex)



try:
	app = ProducerServer(
        	bootstrap_servers=settings.KAFKA_BROKER_URL,
	        client_id="integrator-kafka"
	    )
except Exception as e:
	app = None
	print('Exception in initializing producer')
	print(e)

'''
class Kafka:
	def __init__(self, BROKER):
		self.BROKER = BROKER

	def publish_message(self,producer_instance, topic_name, key, value):
		try:
			key_bytes = bytes(key, encoding='utf-8') if key else None
			value_bytes = bytes(value, encoding='utf-8')
			producer_instance.send(topic_name, key=key_bytes, value=value_bytes)
			producer_instance.flush()
			print('Message published successfully.')
		except Exception as ex:
			print('Exception in publishing message')
			print(ex)

	def connect_kafka_producer(self):
		_producer = None
		try:
			_producer = KafkaProducer(
				#bootstrap_servers=['kafka-broker-0-service:9092','kafka-broker-1-service:9092'],
				#bootstrap_servers="kafka-broker-0-service:9092,kafka-broker-1-service:9092",
				bootstrap_servers=self.BROKER,
				api_version=(0, 10))
		except Exception as ex:
			print('Exception while connecting Kafka')
			print(ex)
		return _producer

app = Kafka(settings.KAFKA_BROKER_URL)
'''
