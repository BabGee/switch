import paho.mqtt.client as mqtt

user_topic = 'rankings/5'

new_ranking = '{"type":"ranking","data":[[{"index":4,"date_time":"05 Oct 2016 10:05:49 AM EAT +0300","type":353708,"description":"Details","name":"Copy Dog Software Limited"}],[{"index":2,"date_time":"05 Oct 2016 10:04:29 AM EAT +0300","type":346170,"description":"Details","name":"Neuteronics Limited"}],[{"index":1,"date_time":"13 Oct 2016 08:02:57 PM EAT +0300","type":45566,"description":"Details","name":"Text Technologies"}],[{"index":3,"date_time":"05 Oct 2016 10:05:29 AM EAT +0300","type":362320,"description":"Details","name":"Aspect Data Limited"}]]}'

new_notification = '{"type":"notification","data":"This is the notification text"}'

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("#")
    client.publish(user_topic,new_ranking)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message


client.username_pw_set("Super@User","apps")
#client.connect("iot.eclipse.org", 1883, 60)
client.connect("127.0.0.1", 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()
