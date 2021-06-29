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
	        client_id="switch-kafka"
	    )
except Exception as e:
	app = None
	print('Exception in initializing producer')
	print(e)

