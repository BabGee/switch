import paho.mqtt.client as paho
import json 
import ssl


mqttc = paho.Client()
 
# Settings for connection
host = "127.0.0.1"
#host= 'APPS001.localdomain'
topic= "testtopic/bar"
rankings_topic = 'rankings/5'

port = 1883

new_ranking ='[[{"index":3,"date_time":"05 Oct 2016 10:05:29 AM EAT +0300","type":362320,"description":"Details","name":"Aspect Data Limited"}],[{"index":4,"date_time":"05 Oct 2016 10:05:49 AM EAT +0300","type":353708,"description":"Details","name":"Copy Dog Software Limited"}],[{"index":2,"date_time":"05 Oct 2016 10:04:29 AM EAT +0300","type":346170,"description":"Details","name":"Neuteronics Limited"}],[{"index":1,"date_time":"13 Oct 2016 08:02:57 PM EAT +0300","type":45566,"description":"Details","name":"Text Technologies"}]]'
 
# Callbacks
def on_connect(client,mosq, obj, rc):
    print("connect rc: "+str(rc))
    print 'most: %s | obj: %s ' % (mosq, obj)
    client.subscribe('/#', 0)

    client.publish(rankings_topic,new_ranking);
 
def on_message(mosq, obj, msg):
    message = None
    try:message = str(json.loads(msg.payload))
    except:message = str(msg.payload)
    print( "Received on topic: " + msg.topic + " Message: "+ message + "\n");
 
def on_subscribe(mosq, obj, mid, granted_qos):
    print("Subscribed OK")
 
# Set callbacks
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_subscribe = on_subscribe
 
# Connect and subscribe
print("Connecting to " +host +"/" +topic)
#mqttc.tls_set("test.crt")
#mqttc.tls_set(ca_certs="/etc/pki/tls/testca/cacert.pem", certfile="/etc/pki/tls/client/cert.pem", keyfile="/etc/pki/tls/client/key.pem", cert_reqs=ssl.CERT_REQUIRED,tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
#mqttc.tls_set(ca_certs="/etc/pki/tls/testca/cacert.pem", tls_version=ssl.PROTOCOL_TLSv1_2)

mqttc.user_data_set({'userdata':'userdata'})
mqttc.username_pw_set("apps","apps")
mqttc.connect(host, port, 60)
 
# Wait forever, receiving messages
#rc = 0
#import time
#while rc <=  200:
#    mqttc.loop()
    #print rc
#    rc+=1
#    time.sleep(2)
mqttc.loop_forever() 
#print("rc: "+str(rc))
