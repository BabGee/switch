import faust
from faust.types import StreamT
#from primary.core.async.faust import app
from switch.faust import app
from .models import *

from primary.core.administration.views import WebService
import logging
lgr = logging.getLogger('secondary.channels.notify')

class Greeting(faust.Record):
    from_name: str
    to_name: str

topic = app.topic('hello-topic', value_type=Greeting)

#@app.discover
@app.agent(topic)
async def hello(greetings):
    async for greeting in greetings:
        print(f'Hello from {greeting.from_name} to {greeting.to_name}')

#@app.discover
@app.timer(interval=1.0)
async def example_sender(app):
    await hello.send(
        value=Greeting(from_name='Faust', to_name='you'),		
    )



'''
class Notification(faust.Record):
    name: str
    score: float
    active: bool


@app.agent()
async def Test(alert: StreamT[Notification]):
	async for a in alert:

		lgr.info('Alert: %s' % a)
		payload = WebService().post_request({}, 'http://192.168.137.21:732/test/notification/')
		lgr.info('Response: %s' % payload)

		yield payload['response']

'''
