#!/usr/bin/env python

import os
import re
import sys
import time
import getopt
import tempfile
import subprocess

class syscmd():
	def __which(self, app):
		def if_exists(fp):
			return os.path.exists(fp) and os.access(fp, os.X_OK)
		fp, fn = os.path.split(app)
		if fp:
			if if_exists(app):
				return app
		else:
			for path in os.environ["PATH"].split(os.pathsep):
				prog = os.path.join(path, app)
				if if_exists(prog):
					return prog
		return app


	def run(self, execCmd):
		execCmd    = execCmd.split( )
		execCmd[0] = self.__which(execCmd[0])
		output     = subprocess.PIPE
	
		time.sleep(.5)
	
		if os.path.exists(execCmd[0]) and os.access(execCmd[0], os.X_OK):
			p = subprocess.Popen(execCmd, stdout=output, stderr=output)
			time.sleep(.5)
			p.wait()
			return p.communicate()[0].rstrip('\n')
		else:
			print 'Unable to execute "%s"!\n' % execCmd[0]
			sys.exit(1)


def main(argv):
	if len(argv) < 2 or len(argv) > 2:
		print '<instance_id> <key_type>\n'
		sys.exit(2)

	for arg in argv:
		if arg == 'rsa' or arg == 'ecdsa' or arg == 'dsa':
			key_type = arg

			if argv.index(arg) == 0:
				instance_id = argv[1]
			elif argv.index(arg) == 1:
				instance_id = argv[0]

	if not 'key_type' in locals():
		print 'No key type detected! (rsa, dsa, ecdsa)\n'
		sys.exit(2)

	scmd = syscmd()
	instance_console_output = ''
	instance_sshkey_output  = {}
	instance_ssh_key_tmp	= tempfile.NamedTemporaryFile(mode = 'w+t')

	instance_privateip = scmd.run('aws ec2 describe-instances --instance-id ' + instance_id + ' --query Reservations[*].Instances[*].PrivateIpAddress')

	if instance_privateip == 'None' or len(instance_privateip) == 0:
		print 'ERROR: Please check the instance id %s\n' % instance_id
		sys.exit(1)

	while len(instance_console_output) < 100:
		instance_console_output = scmd.run('aws ec2 get-console-output --instance-id ' + instance_id)
		time.sleep(10)

        instance_console_output = instance_console_output.split('BEGIN SSH HOST KEY FINGERPRINTS-----', 1)[-1]
        instance_console_output = instance_console_output.split('ec2: -----END SSH HOST KEY FINGERPRINTS', 1)[0]

	for line in instance_console_output.split('\n'):
		if re.search('ec2:', line):
			fixed = line.replace('(', '').replace(')', '').replace('ec2:', '').split( )
			instance_sshkey_output[fixed[3]] = fixed

	if key_type.upper() in instance_sshkey_output:
		print 'SSH public key of type %s found for %s\n' % (key_type.upper(), instance_privateip)
	else:
		print 'ERROR: SSH public key of type %s does not exist for %s\n' % (key_type.upper(), instance_privateip)
		sys.exit(1)

	instance_keyscan = scmd.run('ssh-keyscan -t %s %s' % (key_type, instance_privateip))

	instance_ssh_key_tmp.writelines(['%s\n' % instance_keyscan])
	instance_ssh_key_tmp.seek(0)

	actual_fingerprint = scmd.run('ssh-keygen -lf %s' % instance_ssh_key_tmp.name).split( )[1]

	if actual_fingerprint == instance_sshkey_output[key_type.upper()][1]:
		print 'SSH host key fingerprints match!\n'
		scmd.run('ssh-keygen -R %s' % instance_privateip)
		f = open(os.path.expanduser(os.path.join('~', '.ssh', 'known_hosts')), 'a')
		for line in instance_ssh_key_tmp:
        		f.write(line.rstrip())
		f.write('\n')
		f.close()
		print 'SSH public key added to known_hosts\n'
	else:
		print 'ERROR: SSH host key fingerprints do not match!\n'
		sys.exit(1)

	sys.exit(0)

if __name__ == "__main__":
	main(sys.argv[1:])
