#!/usr/bin/env python
import yaml
import paramiko
import atexit
import logging
import sys
import pprint
import OracleLib


class YamlLoader(object):
    def __init__(self, hosts_file='databases.yml', appliances_file='appliances.yml', plan_yml='plan.yml',
                 connectors_file='connectors.yml'):
        self.oracle_servers = yaml.load(open(hosts_file))
        self.appliances = yaml.load(open(appliances_file))
        self.test_plan = yaml.load(open(plan_yml))
        self.connectors = yaml.load(open(connectors_file))


class OracleCleaner(object):
    def __init__(self):
        ymls = YamlLoader()
        self.oracle_servers = ymls.oracle_servers
        self.appliances = ymls.appliances
        self.test_plan = ymls.test_plan
        self.connectors = ymls.connectors

    def cleanup_diag(self, host_name, test=True):
        ipaddress, password, homes, sids = self._get_oraclelib_params(host_name)

        for i, sid in enumerate(sids):
            oracle_connection = OracleLib.OracleLib(ipaddress, sid=sids[i], home=homes[i], password=password)
            diag_dest = oracle_connection.query("select value from v\$parameter where "
                                                "name like '%background_dump_dest%'")[0]['VALUE'].strip('/trace')
            print('Executing: rm -rf /{0}/alert/*; rm -rf /{0}/trace/*'.format(diag_dest))
            if not test:
                ##### Safety procedures
                try:
                    assert sid in diag_dest or 'log' in diag_dest
                    assert diag_dest != '/'
                    oracle_connection.issue_command_as_root('rm -rf /{0}/audit/*; '
                                                            'rm -rf /{0}/trace/*'.format(diag_dest))
                except AssertionError:
                    print('- - WARNING: invalid diag dest: {0}'.format(diag_dest))
                    print('- - diag dest seems unsafe to rm -rf, Skipping ...')
                    continue

    def cleanup_archivelogs(self, host_name):
        ipaddress, password, homes, sids = self._get_oraclelib_params(host_name)

        for i, sid in enumerate(sids):
            oracle_connection = OracleLib.OracleLib(ipaddress, sid=sids[i], home=homes[i], password=password)
            print('*** Cleaning up logs for {0}'.format(sid))
            r = oracle_connection.rman_cmd('crosscheck archivelog all; delete noprompt archivelog all;')
            print(r)

    def _get_oraclelib_params(self, host_name):
        ipaddress = self.oracle_servers[host_name]['ipaddress']
        try:
            password = self.oracle_servers[host_name]['oracle_pass']
        except KeyError:
            password = '12!pass345'
        homes = [database.values()[0]['oracle_home'] for database in self.oracle_servers[host_name]['databases']]
        sids = [database.values()[0]['oracle_sid'] for database in self.oracle_servers[host_name]['databases']]
        return ipaddress, password, homes, sids


class TestPlanner(object):
    """
    Class used for generating rbc alias files from yml data
    """
    def __init__(self):
        ymls = YamlLoader()
        self.oracle_servers = ymls.oracle_servers
        self.appliances = ymls.appliances
        self.test_plan = ymls.test_plan
        self.connectors = ymls.connectors

    def create_aliases(self, filename='aliases'):
        lines, names = self._create_aliases()
        with open(filename, 'w') as f:
            for line in lines:
                f.write(line + '\n')
        with open('{0}.sh'.format(filename), 'w') as f:
            for name in names:
                execution_string = 'nohup python rbc.py {0} &'.format(name)
                f.write(execution_string + '\n')

    def _create_alias(self, host, database, appliance, test='suites/ora2/logsmart_mounts1.robot'):
        appliance_py = self.appliances[appliance]['inventory_file']
        db_py = ''
        for db_dict in self.oracle_servers[host]['databases']:
            if database in db_dict.keys():
                db_py = db_dict[database]['inventory_file']
        if not db_py:
            raise RuntimeError('Database name: {0} not found for host {1}'.format(database, host))

        alias_name = '[{0}_{1}]'.format(host, database)
        alias_string = 'inv/appliance/{0} inv/host/{1}:host1 inv/host/{1}:host2 {2}'.format(appliance_py, db_py, test)
        return alias_name, alias_string

    def _create_aliases(self):
        alias_lines = []
        alias_names = []
        for host_name, config in self.test_plan.items():
            # Ignore 'connectors' key in yml file
            if host_name == 'connectors':
                continue
            # Create aliases for all databases
            for db_dict in self.oracle_servers[host_name]['databases']:
                host = host_name
                database = db_dict.keys()[0]
                appliance = config['appliance']
                alias_definition, alias_string = self._create_alias(host, database, appliance)
                alias_name = alias_definition.strip('[').strip(']')
                alias_names.append(alias_name)
                alias_lines.append(alias_definition)
                alias_lines.append(alias_string)
                alias_lines.append('')

        return alias_lines, alias_names


class UpgradeController(object):
    def __init__(self):
        # Load ymls database
        ymls = YamlLoader()
        self.oracle_servers = ymls.oracle_servers
        self.appliances = ymls.appliances
        self.test_plan = ymls.test_plan
        self.connectors = ymls.connectors

    def print_host_info(self, host_name):
        connector, platform, databases = self.get_host_info(host_name)
        print('- connector version: . . {0}'.format(connector))
        print('- platform . . . . . . . {0}'.format(platform))
        print('- databases processes  . {0}'.format(databases))

    def get_host_info(self, host_name):
        ipaddress = self.oracle_servers[host_name]['ipaddress']
        platform = self.oracle_servers[host_name]['platform']
        a = HostConnection(ipaddress)

        # Show connector version
        connector = a.raw('cat /act/etc/key.txt')[0][0].strip('\n')

        # List all running databases
        r = a.raw('ps -ef | grep [p]mon')
        databases = [line.split('pmon_')[1].strip('\n') for line in r[0]]
        return connector, platform, databases

    def upgrade_connector(self, host_name, config):
        """
        performs 3 tasks:
        - curl package
        - uninstall current connector version (if any)
        - install package
        :param hostname: e.g. 'rh66orarac1'. Defined in databases.yml
        :param config:  e.g. 'trunk'. Defined in plan.yml
        :return:
        """
        try:
            ipaddress = self.oracle_servers[host_name]['ipaddress']
        except KeyError('Oracle server named: {0} not found in yml'.format(host_name)):
            return 1

        platform = self.oracle_servers[host_name]['platform']
        gpg_path = self.test_plan['connectors'][config]
        curl_string = self.connectors['curl_binaries'][platform]
        gpg_full_path, filename = self._get_gpg_path(host_name, gpg_path)
        a = HostConnection(ipaddress)

        print('\n')
        print('**** HOST : {0} ****'.format(host_name))

        try:
            a.test_connection()
        except RuntimeError:
            print('Unable to connect to {0}, skipping'.format(ipaddress))
            return

        if not config:
            print('No config passed in, skipping upgrade for {0}'.format(host_name))
            return
        # Curl latest patch package

        print('CURL connector ****')

        # This is a fix for wget, it does not like https
        if 'wget' in curl_string:
            gpg_full_path = gpg_full_path.split('https://')[1]
        curl_string = '{0} {1}'.format(curl_string, gpg_full_path)
        print('Command: {0}'.format(curl_string))
        out, err, rc = a.raw(curl_string)
        print(rc)
        # If 404 error occurs
        if rc == 1:
            print('** ERROR: CURL could not find {0}. Skipping this host... **'.format(gpg_full_path))
            print(err)
            return

        # Uninstall existing connector
        print('Uninstall connector ****')
        uninstall_command = self.connectors['uninstall_commands'][platform]
        print('Command: {0}'.format(uninstall_command))
        out, err, rc = a.raw(uninstall_command)
        print(rc)

        # Install latest connector
        print('Install connector ****')
        file_path = '/tmp/{0}'.format(filename)
        install_command = self.connectors['install_commands'][platform]
        install_command = install_command.replace('FILENAME', file_path)
        print('Command: {0}'.format(install_command))
        out, err, rc = a.raw(install_command)
        print(rc)

        print('Cat /act/etc/key.txt ****')
        out, err, rc = a.raw('cat /act/etc/key.txt')
        print(out)

    def upgrade_connectors(self):
        for host_name, config in self.test_plan.items():
            if host_name == 'connectors':
                continue
            self.upgrade_connector(host_name, config['branch'])

    def _get_gpg_path(self, host_name, branch_path):
        # Correct if trailing slash in path
        if branch_path[-1] == '/':
            branch_path = branch_path[:-1]
        connector_version = branch_path.split('/')[-1]
        platform_key = self.oracle_servers[host_name]['platform']
        platform_name = self.connectors['platform_names'][platform_key]
        platform_format = self.connectors['platform_formats'][platform_key]
        gpg_name = 'connector-{0}-{1}.{2}'.format(platform_name, connector_version, platform_format)
        gpg_full_path = '{0}/{1}'.format(branch_path, gpg_name)
        return gpg_full_path, gpg_name


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


# UNIT TESTS
# # Unit test for TestPlanner
# a = TestPlanner()
# a.create_aliases()
#
# # Unit test for HostUpgrader
# a = UpgradeController()
# a.upgrade_connectors()

def print_help():
    print('')
    print('*** Oracle Regression Environment Manager ***')
    print('HELP:')
    print('ore upgradehosts: upgrade host connectors according to testplan')
    print('ore upgradehost <hostname> <branch>: upgrade a single host')
    print('ore lshost <hostname>: print host information')
    print('')
    print('ore cleanuplogs <hostname>: cleans up archivelogs')
    print('ore cleanupdiag <hostname>: cleans up trace, audit files')
    print('ore cleanup<type> all: cleans up all hosts in databases.yml')
    print('')
    print('ore aliases <filename>: create aliases file for use with rbc')
    print('')
    print('ore testplan : prints the oracle test plan to the screen')
    print('ore databases: prints all the hosts, databases, and their information')
    print('ore appliances: prints all the appliances, and their information')
    print('')

if __name__ == '__main__':
    tp = TestPlanner()
    uc = UpgradeController()
    oc = OracleCleaner()

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.lower() in ['upgradehosts']:
            uc.upgrade_connectors()
        elif arg.lower() in ['cleanuplogs', 'rmlogs']:
            if sys.argv[2] in ['all', '-a', '-A', 'a', 'A']:
                hosts = [host for host in oc.test_plan.keys() if host != 'connectors']
                for host in hosts:
                    print('**** {0}'.format(host))
                    oc.cleanup_archivelogs(host)
            else:
                try:
                    oc.cleanup_archivelogs(sys.argv[2])
                except KeyError:
                    print('Host not found!')
        elif arg.lower() in ['cleanupdiag', 'cleandiag', 'rmdiag']:
            if sys.argv[2] in ['all', '-a', '-A', 'a', 'A']:
                hosts = [host for host in oc.test_plan.keys() if host != 'connectors']
                for host in hosts:
                    print('**** {0}'.format(host))
                    oc.cleanup_diag(host, test=False)
            else:
                try:
                    oc.cleanup_diag(sys.argv[2], test=False)
                except KeyError:
                    print('Host not found!')
        elif arg.lower() in ['upgradehost', 'upgrade']:
            if len(sys.argv) < 4:
                print('Format: ore upgradehost <hostname> <branch>')
            else:
                uc.upgrade_connector(sys.argv[2], sys.argv[3])
        elif arg.lower() in ['aliases']:
            if len(sys.argv) > 2:
                tp.create_aliases(filename=sys.argv[2])
            else:
                tp.create_aliases()
        elif arg.lower() in ['testplan', 'plan']:
            pprint.pprint(tp.test_plan)
        elif arg.lower() in ['appliances', 'appliance']:
            pprint.pprint(tp.appliances)
        elif arg.lower() in ['databases', 'hosts', 'servers']:
            pprint.pprint(tp.oracle_servers)
        elif arg.lower() in ['hostinfo', 'lshost', 'ls']:
            if len(sys.argv) > 2:
                uc.print_host_info(sys.argv[2])
            else:
                print('Specify hostname')
        elif arg.lower() in ['lshosts']:
            hosts = [host for host in oc.test_plan.keys() if host != 'connectors']
            for host in hosts:
                print('**** {0}'.format(host))
                uc.print_host_info(host)
        else:
            print_help()
    else:
        print_help()
