

# service
- enabled logs to transactions table
- poller do not log to transactions table


#### Last Response
- last_response used to specify a response based on the status code
`status_code%response|status_code2%response`

if none of the status codes match, the service command response will be used
> todo more on the service command response
 

the 2 below apply when last_response is null or ''
- failed_last_response  response returned when status code is not 00
- success_last_response response returned when status code is 00
