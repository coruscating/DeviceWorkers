import string
import os
import traceback
FILEDIR = os.path.dirname(os.path.abspath(__file__))+'/'
maps = open(FILEDIR + 'DAC_to_electrode_map.csv')

electrode_hoa_dict = {}

for line in maps:
	try:
		val=line.split(',')
		if 'SMA' in val[3]:
			electrode_hoa_dict[val[5].strip(' ')] = '%s'%(val[3].strip(' '))
		else:
			electrode_hoa_dict[val[5].strip(' ')] = 'DAC%s-%s'%(val[2].strip(' '),val[3].strip(' '))

	except Exception as e:
		print traceback.format_exc()
		print e
		pass	
print electrode_hoa_dict