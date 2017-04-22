
			'''		
        	                                lgr.info('File Size: %s' % file.size)
						try: lgr.info('Blob Read'); xs=file.read();lgr.info('Blob: %s' % xs);
						except: lgr.info('No Blob Read');
						lgr.info('Content Type : %s' % str(file.content_type))
						extension_chunks = str(file).split('.')
						extension = extension_chunks[len(extension_chunks)-1]
						extension = extension if len(extension)<=4 else str(file.content_type).split('/')[1]
						lgr.info('Extenstion: %s' % str(extension))
						filename = "%s_%s_%s" % (profile_id, payload['timestamp'],extension_chunks[0])
						filename = "%s.%s" % (base64.urlsafe_b64encode(filename), extension)


						if  int(file.size) > 10000000 or str(file.content_type) not in  ['image/jpeg', 'image/png']:
							payload['response'] = 'FAIL | Please check the upload type, file size and extension'
						else:
							dir_name = '/srv/applications/regix/gui/static/images/ocr/scans/'
							
							#lgr.info('URL: %s, ROOT: %s' % (settings.MEDIA_URL, settings.MEDIA_ROOT))
							#dir_name = str(settings.MEDIA_ROOT) + '/' + str(staff.group.gateway.name.replace(' ','_'))

							#file_name = str(file) + '/' + filename
							#full_path = dir_name + '/' +file_name
							full_path = dir_name + filename
							lgr.info('There is a full path: %s' % full_path)
							with open(full_path, 'wb+') as destination:
								for chunk in file.chunks():
									destination.write(chunk)
								destination.close()
							#payload['response'] = 'OK | File Uploaded, please come back after a minute to allow processing'
							

					lgr.info('File Exists: %s File: %s' % (exists, filename))
			'''



