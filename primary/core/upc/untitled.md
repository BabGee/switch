	def validate_institution(self, payload, node_info):
		try:
			gateway_profile = GatewayProfile.objects.get(id=payload['gateway_profile_id'])
			if gateway_profile.institution:
				if 'institution_id' in payload.keys() and str(payload['institution_id']).strip() == str(gateway_profile.institution.id):
					payload['response'] = 'Institution Validated'
					payload['response_status'] = '00'
				elif 'institution_id' not in payload.keys():
					payload['institution_id'] = gateway_profile.institution.id
					payload['response'] = 'Institution Captured'
					payload['response_status'] = '00'
				else:
					payload['response_status'] = '03'
					payload['response'] = 'Institution did not match profile'
			else:
				payload['response_status'] = '25'
				payload['response'] = 'Profile Institution Does not Exist %s' % gateway_profile

		except Exception as e:
			lgr.info('Error on validating institution: %s' % e)
			payload['response_status'] = '96'
		return payload

	def get_institution(self, payload, node_info):
		if 'institution_id' in payload.keys():
			institution = Institution.objects.get(id=payload['institution_id'])
		elif 'institution_id' not in payload.keys(): 
			payload['institution_id'] = gateway_profile.institution.id
			institution = Institution.objects.get(id=payload['institution_id'])
		return institution    