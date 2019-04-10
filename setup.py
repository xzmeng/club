import subprocess
import os

if os.path.exists('data-dev.sqlite'):
    os.remove('data-dev.sqlite')


subprocess.run(['rm', '-rf', 'migrations'])
subprocess.run(['flask', 'db', 'init'])
subprocess.run(['flask', 'db', 'migrate'])
subprocess.run(['flask', 'db', 'upgrade'])
