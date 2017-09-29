import paramiko
import logging
import atexit


class HostConnection(object):
    def __init__(self, ipaddress, username='root', password='12!pass345', port=22, **kwargs):

        # Connection params
        self.ipaddress = ipaddress
        self.username = username
        self.password = password
        self.port = port

        # Dictionary of update commands
        self.connection_params = kwargs

        # Connect
        self.client = None

    def scp_script(self, path):
        if not self.client:
            self.client = self.connect()

        sftp = self.client.open_sftp()
        filename =  path.split('/')[-1]
        sftp.put(path, '/tmp/{0}'.format(filename))

    def raw(self, command, ignore_error=False):
        """
        Wrapper for paramiko exec_command

        :param command: command to issue over ssh
        :param ignore_error: whether to raise error, or ignore
        :return: (stdout, stderr, rc)
        """
        if not self.client:
            self.client = self.connect()

        stdin, stdout, stderr = self.client.exec_command(command, timeout=800)
        stdin.close()
        rc = stdout.channel.recv_exit_status()
        stdout = stdout.readlines()
        stderr = stderr.readlines()
        return stdout, stderr, rc

    def test_connection(self):
        self.raw('ls')

    def connect(self):
        """
        Connect to remote host

        :return: paramiko SSHClient object
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            print('Connecting to {0} ****'.format(self.ipaddress))
            client.connect(self.ipaddress, username=self.username, password=self.password,
                           port=self.port, **self.connection_params)
        except:
            raise RuntimeError('Could not connect to {0}'.format(self.ipaddress))

        # Turn off timeout of SSH connection
        _, out, _ = client.exec_command("unset TMOUT")
        rc = out.channel.recv_exit_status()
        if rc != 0:
            raise RuntimeError(
                "Return code of 'unset TMOUT was {}.".format(rc))
        # Close this connection after execution
        atexit.register(self.ssh_disconnect)
        return client

    def ssh_disconnect(self):
        try:
            self.ssh_client.close()
        except (AttributeError, NameError):
            logging.debug("No ssh client to close.")
        self.client = None