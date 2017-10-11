import paho.mqtt.client as mqtt
#from django.core.serializers.json import DjangoJSONEncoder
#import json


class MqttServerClient(object):

    def __init__(self):

        client = mqtt.Client()
        client.username_pw_set("guest", "guest")
        client.connect("127.0.0.1", 1883, 60)

        self.client = client

    def publish(self,channel,payload):
        self.client.publish(
            channel,
            payload#json.dumps(bid_change, cls=DjangoJSONEncoder)
        )

    def disconnect(self):
        self.client.disconnect()
