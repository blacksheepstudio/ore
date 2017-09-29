#!/usr/bin/env python
import yaml
import paramiko
import atexit
import logging
import sys
import pprint
from lib import OracleLib
import csv


class YamlLoader(object):
    def __init__(self):
        self.oracle_servers = yaml.load(open('yaml/databases.yml'))
        self.appliances = yaml.load(open('yaml/appliances.yml'))
        self.test_plan = yaml.load(open('yaml/plan.yml'))
        self.connectors = yaml.load(open('yaml/connectors.yml'))
        self.executions = yaml.load(open('yaml/executions.yml'))


class ScriptExecutor(YamlLoader):
    def __init__(self):
        super(ScriptExecutor, self).__init__()

    def execute_permissions_check(self, host_name):
        ipaddress = self.oracle_servers[host_name]['ipaddress']
        connection = HostConnection(ipaddress)

        print('** Sending scripts to {0}'.format(host_name))
        connection.scp_script('host_scripts/chkperms.sh')
        connection.scp_script('host_scripts/chkperms.txt')

        print('** Executing: /tmp/chkperms.sh')
        connection.raw('chmod 777 /tmp/chkperms.sh; chmod 777 /tmp/chkperms.txt')
        r = connection.raw('cd /tmp; ./chkperms.sh')
        print(r[1])
        for line in r[0]:
            print(line.strip('\n'))


class HostInventoryCreator(YamlLoader):
    """ Create Oracle RobotFrameWork inventory files on the fly """
    def __init__(self):
        super(HostInventoryCreator, self).__init__()

    def create_all_inventory(self):
        for hostname, host_dict in self.oracle_servers.items():
            for dbname, db_dict in host_dict['databases'].items():
                self._create_inventory_file(hostname, dbname)
        print('All host inventory files have been created in ./inv/host')
        for hostname, app_dict in self.appliances.items():
            self._create_appliance_inventory_file(hostname)
        print('All appliance inventory files have been created in ./inv/appliance')

    def _create_appliance_inventory_file(self, hostname):
        """ Creates appliance inventory file """

        appliance = self.appliances[hostname]
        appliance_ip = appliance['ipaddress']
        dict_kvs = []
        dict_kvs.append("'hostname': '{0}'".format(hostname))
        dict_kvs.append("'appliance_ip': '{0}'".format(appliance_ip))
        dict_kvs.append("'user': 'admin'")
        dict_kvs.append("'pass': 'password'")
        dict_kvs.append("'ssh_user': 'root'")
        dict_kvs.append("'ssh_pass': 'actifio2'")

        # Join elements together into python code dictionary format
        variables = ', '.join(dict_kvs)
        variables_string = 'variables = {' + variables + '}'

        # This is what the final .py file will look like
        lines = []
        lines.append('from rf_inventory import get_appliance_variables')
        lines.append('')
        lines.append(variables_string)
        lines.append('')
        lines.append('')
        lines.append("def get_variables(prepend=None, append=None, delimiter='.', base=variables):")
        lines.append("    return get_appliance_variables(base=base, prepend=prepend, "
                     "append=append, delimiter=delimiter)")

        # Write to file
        filename = hostname + '.py'
        file_path = 'inv/appliance/{0}'.format(filename)
        with open(file_path, 'w') as f:
            for line in lines:
                f.write(line + '\n')
        print('Created appliance inventory: inv/appliance/{0}'.format(filename))

    def _create_inventory_file(self, hostname, database):
        """
        Creates an inventory file given a hostname and database
        :param hostname: hostname in databases.yml
        :param database: database name in databases.yml
        :return:
        """
        # Gather facts for inventory file data from yamls
        dict_kvs = []
        dict_kvs.append("'name': '{}'".format(hostname))
        ip = self.oracle_servers[hostname]['ipaddress']
        dict_kvs.append("'ip': '{}'".format(ip))
        dict_kvs.append("'ssh_user': 'root'")
        dict_kvs.append("'ssh_pass': '12!pass345'")
        dict_kvs.append("'ssh_private_key_file': ''")
        dict_kvs.append("'app': '{0}'".format(database))
        dict_kvs.append("'app_type': 'Oracle'")
        dict_kvs.append("'apps': ['/', '{0}']".format(database))
        dict_kvs.append("'app_list': ['/', '{0}']".format(database))
        dict_kvs.append("'app_exclude': ['/']")

        platform = self.oracle_servers[hostname]['databases'][database]['testlink_platform']
        if 'asm' in platform.lower():
            dict_kvs.append("'cluster_ip': '{0}'".format(ip))
            dict_kvs.append("'racnodelist': '{0}'".format(ip))
        else:
            dict_kvs.append("'cluster_ip': None")
            dict_kvs.append("'racnodelist': None")

        oracle_sid = self.oracle_servers[hostname]['databases'][database]['oracle_sid']
        oracle_home = self.oracle_servers[hostname]['databases'][database]['oracle_home']
        oracle_path = oracle_home + '/bin'
        tnsadmindir = oracle_home + '/network/admin'
        dict_kvs.append("'oracle_user': 'oracle'")
        dict_kvs.append("'oracle_pass': '12!pass345'")
        dict_kvs.append("'oracle_sid': '{0}'".format(oracle_sid))
        dict_kvs.append("'oracle_home': '{0}'".format(oracle_home))
        dict_kvs.append("'oracle_path': '{0}'".format(oracle_path))
        dict_kvs.append("'po_databasesid': 'achild'")
        dict_kvs.append("'po_username': 'oracle'")
        dict_kvs.append("'po_orahome': '{0}'".format(oracle_home))
        dict_kvs.append("'po_tnsadmindir': '{0}'".format(tnsadmindir))
        dict_kvs.append("'po_totalmemory': '800'")
        dict_kvs.append("'po_sgapct': '70'")

        # Join elements together into python code dictionary format
        variables = ', '.join(dict_kvs)
        variables_string = 'variables = {' + variables + '}'

        # This is what the final .py file will look like
        lines = []
        lines.append('from rf_inventory import get_host_variables')
        lines.append('')
        lines.append(variables_string)
        lines.append('')
        lines.append('')
        lines.append("def get_variables(prepend=None, append=None, delimiter='.', base=variables):")
        lines.append("    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)")

        # Write to file
        filename = self.oracle_servers[hostname]['databases'][database]['inventory_file']
        file_path = 'inv/host/{0}'.format(filename)
        with open(file_path, 'w') as f:
            for line in lines:
                f.write(line + '\n')
        print('Created inv/host{0}'.format(filename))


class ExecutionPlanner(YamlLoader):
    """ Create aliases file and aliases.sh from executions file """
    def __init__(self):
        super(ExecutionPlanner, self).__init__()

    def create_aliases(self):
        final_lines = []
        final_names = []
        filename = 'aliases'
        for execution_plan, data_dict in self.executions['executions'].items():
            for layer in data_dict['layers']:
                lines, names = self._create_aliases(execution_plan, layer=layer)
                final_lines += lines
                final_names += names
            with open(filename, 'w') as f:
                for line in final_lines:
                    f.write(line + '\n')
            with open('{0}.sh'.format(filename), 'w') as f:
                for name in final_names:
                    execution_string = 'nohup python rbc.py {0} &'.format(name)
                    f.write(execution_string + '\n')

    def _create_alias(self, host, database, appliance, variables='',
                      test='suites/ora2/logsmart_mounts1.robot', layer='', execution=''):
        appliance_py = self.appliances[appliance]['inventory_file']

        try:
            db_py = self.oracle_servers[host]['databases'][database]['inventory_file']
        except KeyError:
            raise RuntimeError('Database name: {0} not found for host {1}'.format(database, host))

        alias_name = '[{0}_{1}_{2}_{3}]'.format(host, database, execution, layer)
        alias_string = 'inv/appliance/{0} inv/host/{1}:host1 inv/host/{1}:host2'.format(appliance_py, db_py)
        if variables:
            alias_string = alias_string + ' ' + variables
        alias_string = alias_string + ' ' + test
        return alias_name, alias_string

    def _create_aliases(self, execution_name, layer):
        alias_lines = []
        alias_names = []
        for hostname, hostname_dict in self.executions['layers'][layer].items():
            host = hostname
            database = hostname_dict['database']
            appliance = self.test_plan[host]['appliance']
            variables = self.executions['executions'][execution_name]['variables']
            alias_definition, alias_string = self._create_alias(host, database, appliance, variables,
                                                                layer=layer, execution=execution_name)
            print(alias_definition)
            print(alias_string)
            alias_name = alias_definition.strip('[').strip(']')
            alias_names.append(alias_name)
            alias_lines.append(alias_definition)
            alias_lines.append(alias_string)
            alias_lines.append('')
        return alias_lines, alias_names


class CSVGenerator(YamlLoader):
    """
    Generates a CSV of the current test plan
    """
    def __init__(self, plan='plan.yml'):
        super(CSVGenerator, self).__init__()

    def create_csv(self, filename='plan.csv'):
        column_labels = ['platform', 'testlink_platform', 'oracle_version', 'oracle_sid', 'host_name', 'ipaddress',
                          'uds_version', 'appliance', 'result', 'notes']

        final_rows = []
        host_names = [host for host in oc.test_plan.keys() if host != 'connectors']
        for host_name in host_names:
            ipaddress = self.oracle_servers[host_name]['ipaddress']
            platform = self.oracle_servers[host_name]['platform']
            uds_version = self.test_plan[host_name]['branch']
            appliance = self.test_plan[host_name]['appliance']

            for k, database in self.oracle_servers[host_name]['databases'].items():
                oracle_sid = database['oracle_sid']
                oracle_version = database['version']
                testlink_platform = database['testlink_platform']
                final_rows.append([platform, testlink_platform, oracle_version, oracle_sid,
                                   host_name, ipaddress, uds_version, appliance,
                                  '', ''])
        final_rows.sort(key=lambda x: x[0])
        final_rows.insert(0, column_labels)

        with open(filename, 'w') as myfile:
            wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
            for row in final_rows:
                wr.writerow(row)


class OracleCleaner(YamlLoader):
    def __init__(self):
        super(OracleCleaner, self).__init__()

    def cleanup_diag(self, host_name, test=True):
        """ This command will query the background_dump_dest in the database then, as Oracle user will
        issue rm -rf commands on the data within the trace and audit folders.

        WARNING: This has the potential to go horribly wrong, I have put some safety measures in place,
        but there is no guarantee that something horrible will not happen """

        ipaddress, password, homes, sids = self._get_oraclelib_params(host_name)

        for i, sid in enumerate(sids):
            oracle_connection = OracleLib.OracleLib(ipaddress, sid=sids[i], home=homes[i], password=password)
            try:
                diag_dest = oracle_connection.query("select value from v\$parameter where "
                                                    "name like '%background_dump_dest%'")[0]['VALUE'].strip('/trace')
                print('Executing: rm -rf /{0}/alert/*; rm -rf /{0}/trace/*'.format(diag_dest))
                if not test:
                    # Safety procedures
                    try:
                        assert sid in diag_dest or 'log' in diag_dest
                        assert diag_dest != '/'
                        oracle_connection.issue_command_as_root('rm -rf /{0}/audit/*; '
                                                                'rm -rf /{0}/trace/*'.format(diag_dest))
                    except AssertionError:
                        print('- - WARNING: invalid diag dest: {0}'.format(diag_dest))
                        print('- - diag dest seems unsafe to rm -rf, Skipping ...')
                        continue
            except OracleLib.OracleError as e:
                print('Something went wrong with DB: {0}'.format(sid))
                print('Message: {0}'.format(e.errormessage))

    def cleanup_archivelogs(self, host_name):
        ipaddress, password, homes, sids = self._get_oraclelib_params(host_name)

        for i, sid in enumerate(sids):
            oracle_connection = OracleLib.OracleLib(ipaddress, sid=sids[i], home=homes[i], password=password)
            print('*** Cleaning up logs for {0}'.format(sid))
            try:
                r = oracle_connection.rman_cmd('crosscheck archivelog all; delete noprompt archivelog all;')
                print(r)
            except OracleLib.RMANError as e:
                print(e.errorcode, e.errormessage)
            except RuntimeError:
                print('ERROR: Something went wrong, is {0} open?'.format(sid))

    def _get_oraclelib_params(self, host_name):
        ipaddress = self.oracle_servers[host_name]['ipaddress']
        try:
            password = self.oracle_servers[host_name]['oracle_pass']
        except KeyError:
            password = '12!pass345'
        homes = [database['oracle_home'] for k, database in
                 self.oracle_servers[host_name]['databases'].items()]
        sids = [database['oracle_sid'] for k, database in
                self.oracle_servers[host_name]['databases'].items()]
        return ipaddress, password, homes, sids


class TestPlanner(YamlLoader):
    """
    Class used for generating rbc alias files from yml data
    """
    def __init__(self):
        super(TestPlanner, self).__init__()


class UpgradeController(YamlLoader):
    def __init__(self):
        super(UpgradeController, self).__init__()

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
        print(err, rc)
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
        print(err, rc)

        # Install latest connector
        print('Install connector ****')
        file_path = '/tmp/{0}'.format(filename)
        install_command = self.connectors['install_commands'][platform]
        install_command = install_command.replace('FILENAME', file_path)
        print('Command: {0}'.format(install_command))
        out, err, rc = a.raw(install_command)
        print(err, rc)

        print('cat /act/etc/key.txt ****')
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


# CLI

def print_help():
    """ Display on-screen list of CLI options """
    print('')
    print('*** Oracle Regression Environment Manager ***')
    print('')
    print('[TestPlan commands]')
    print(' ore mkcsv: create blank testplan csv file')
    print(' ore mkinv: create RobotFramework inventory for hosts/appliances')
    print(' ore aliases: create rbc aliases file from executions.yml')
    print('')
    print('[Host connector upgrade commands]')
    print(' ore upgradehosts: upgrade host connectors according to testplan')
    print(' ore upgradehost <hostname> <branch>: upgrade a single host')
    print('')
    print('[Host info commands]')
    print(' ore lshost <hostname>: gather host information from given host')
    print(' ore lshosts <hostname>: gather host information from all hosts')
    print('')
    print('[Host cleanup commands]')
    print(' ore cleanuplogs <hostname>: cleans up archivelogs')
    print(' ore cleanupdiag <hostname>: cleans up trace, audit files')
    print(' ore cleanup<type> all: cleans up all hosts in databases.yml')
    print('')
    print('[YAML info commands]')
    print(' ore testplan : prints the oracle test plan to the screen')
    print(' ore databases: prints all the hosts, databases, and their information')
    print(' ore appliances: prints all the appliances, and their information')
    print('')


if __name__ == '__main__':
    oc = OracleCleaner()
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        # Upgrade all host connectors according to plan.yml
        if arg.lower() in ['upgradehosts']:
            uc = UpgradeController()
            uc.upgrade_connectors()

        # Cleanup archivelogs on given host(s)
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

        # Cleanup diag artifacts on given hosts(s)
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

        # Upgrade given connector on given host
        elif arg.lower() in ['upgradehost', 'upgrade']:
            if len(sys.argv) < 4:
                print('Format: ore upgradehost <hostname> <branch>')
            else:
                uc = UpgradeController()
                uc.upgrade_connector(sys.argv[2], sys.argv[3])

        # Execute custom script
        elif arg.lower() in ['execute', 'script']:
            if len(sys.argv) < 3:
                print('Format: ore script <hostname> <script_name>')
                print('Scripts: permissions, ')
            else:
                se = ScriptExecutor()
                if sys.argv[3] == 'permissions':
                    se.execute_permissions_check(sys.argv[2])
                else:
                    print('Unknown script name')

        # Create RobotFramework inventory file for given host and database
        elif arg.lower() in ['mkinv']:
            if len(sys.argv) > 3:
                ic = HostInventoryCreator()
                ic._create_inventory_file(sys.argv[2], sys.argv[3])
            else:
                if len(sys.argv) > 2:
                    if sys.argv[2] in ['all', '-a', 'ALL']:
                        ic = HostInventoryCreator()
                        ic.create_all_inventory()
                else:
                    print('To create inventory file: ore mkinv <hostname> <dbname>')
                    print('To create all inventory files: ore mkinv all')

        # Create aliases file using data from plan.yml and executions.yml
        elif arg.lower() in ['aliases']:
            tp = ExecutionPlanner()
            tp.create_aliases()

        # Create csv file outlining execution plan
        elif arg.lower() in ['mkcsv']:
            if len(sys.argv) > 2:
                filename = sys.argv[2]
                if '.csv' not in filename:
                    filename += '.csv'
                a = CSVGenerator()
                print('Generating test plan CSV')
                a.create_csv(filename)
            else:
                print('Format should be: ore mkcsv <filename.csv>')

        # Print testplan information
        elif arg.lower() in ['testplan', 'plan']:
            tp = TestPlanner()
            pprint.pprint(tp.test_plan)

        # List appliances
        elif arg.lower() in ['appliances', 'appliance']:
            tp = TestPlanner()
            pprint.pprint(tp.appliances)

        # List databases and information
        elif arg.lower() in ['databases', 'hosts', 'servers']:
            tp = TestPlanner()
            pprint.pprint(tp.oracle_servers)

        # Gather facts from given host
        elif arg.lower() in ['hostinfo', 'lshost', 'ls']:
            if len(sys.argv) > 2:
                uc = UpgradeController()
                uc.print_host_info(sys.argv[2])
            else:
                print('Specify hostname')

        # Gather facts from all hosts in test plan
        elif arg.lower() in ['lshosts']:
            uc = UpgradeController()
            hosts = [host for host in oc.test_plan.keys() if host != 'connectors']
            for host in hosts:
                print('**** {0}'.format(host))
                try:
                    uc.print_host_info(host)
                except RuntimeError as e:
                    print('Something went wrong, unable to connect?')
                    print(e.message)
        else:
            print_help()
    else:
        print_help()
