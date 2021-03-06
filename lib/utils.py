import yaml
import csv
from lib.colors import bcolors
from lib import OracleLib
from lib.hostconnection import HostConnection

cprint = bcolors().cprint


class YamlLoader(object):
    def __init__(self):
        self.oracle_servers = yaml.load(open('yaml/databases.yml'))
        self.appliances = yaml.load(open('yaml/appliances.yml'))
        self.test_plan = yaml.load(open('yaml/plan.yml'))
        self.connectors = yaml.load(open('yaml/connectors.yml'))
        self.executions = yaml.load(open('yaml/executions.yml'))


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
        try:
            system_user = self.oracle_servers[hostname]['databases'][database]['system_user']
	    system_pass = self.oracle_servers[hostname]['databases'][database]['system_pass']
        except KeyError:
            system_user = 'sys'
            system_pass = 'sysman00'

        dict_kvs.append("'ip': '{}'".format(ip))
        dict_kvs.append("'ssh_user': 'root'")
        dict_kvs.append("'ssh_pass': '12!pass345'")
        dict_kvs.append("'ssh_private_key_file': ''")
        dict_kvs.append("'system_user': '{0}'".format(system_user))
        dict_kvs.append("'system_pass': '{0}'".format(system_pass))
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
        filename = 'aliases'
	
	# clear file
	with open(filename, 'w') as f:
		f.write('# Aliases file autogenerated\n')
	with open('{0}.sh'.format(filename), 'w') as f:
		f.write('# Execution script, autogenerated\n')

        for execution_plan, data_dict in self.executions['executions'].items():
            for layer in data_dict['layers']:
                lines, names = self._create_aliases(execution_plan, layer=layer)
                 
                with open(filename, 'a') as f:
                    for line in lines:
                        f.write(line + '\n')
                with open('{0}.sh'.format(filename), 'a') as f:
                    for name in names:
                        execution_string = 'sleep 60; python rbc.py {0} &'.format(name)
                        f.write(execution_string + '\n')
		    f.write('wait\n')

    def _create_alias(self, host, database, appliance, variables='',
                      test='suites/ora2/logsmart_mounts1.robot', layer='', execution=''):
        appliance_py = self.appliances[appliance]['inventory_file']

        try:
            db_py = self.oracle_servers[host]['databases'][database]['inventory_file']
        except KeyError:
            raise RuntimeError('Database name: {0} not found for host {1}'.format(database, host))

        alias_name = '[{0}_{1}_{2}_{3}]'.format(host, database, execution, layer)
        alias_string = 'inv/appliance/{0} inv/host/{1}:host1 inv/host/{1}:host2'.format(appliance_py, db_py)
        # Let's override child database name and grandchild database name here to be:
        # <first seven letters of database_name>a for the child AND,
        # <first seven letters of database_name>b for the grandchild
        childname = database[:-1] + 'x'
        gchildname = database[:-1] + 'y'
        child_variables = 'childname={0} gchildname={1}'.format(childname, gchildname)

        # If there are any -v variables to go to Robot, add here
        if variables:
            alias_string = alias_string + ' ' + variables

        alias_string = alias_string + ' ' + child_variables + ' ' + test
        return alias_name, alias_string

    def _create_aliases(self, execution_name, layer):
        alias_lines = []
        alias_names = []
        for hostname, hostname_dict in self.executions['layers'][layer].items():
            host = hostname
            database = hostname_dict['database']
            appliance = self.test_plan[host]['appliance']
            variables = self.executions['executions'][execution_name]['variables']
            test = self.executions['executions'][execution_name]['suite']
            alias_definition, alias_string = self._create_alias(host, database, appliance, variables,
                                                                layer=layer, test=test, execution=execution_name)
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
        column_labels = ['platform', 'host_name', 'ipaddress', 'oracle_version', 'oracle_sid',
                         'appliance', 'dbauth result', 'osauth result', 'non-logmsart result',
                         'osauth non-logsmart result']

        final_rows = []
        host_names = [host for host in self.test_plan.keys() if host != 'connectors']
        for host_name in host_names:
            ipaddress = self.oracle_servers[host_name]['ipaddress']
            platform = self.oracle_servers[host_name]['platform']
            appliance = self.test_plan[host_name]['appliance']

            for k, database in self.oracle_servers[host_name]['databases'].items():
                oracle_sid = database['oracle_sid']
                oracle_version = database['version']
                final_rows.append([platform, host_name, ipaddress, oracle_version, oracle_sid,
                                   appliance, '', '', '', ''])
        final_rows.sort(key=lambda x: x[0])
        final_rows.insert(0, column_labels)

        # Add gap in between rows where the platform has changed
        insert_indexes = []
        for i, row in enumerate(final_rows):
            try:
                if final_rows[i+1][0] != row[0]:
                    insert_indexes.append(i+1)
            except IndexError:
                continue
        for i, index in enumerate(insert_indexes):
            final_rows.insert(index+i, ['', '', '', '', '', '', '', '', '', ''])

        with open(filename, 'w') as myfile:
            wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
            for row in final_rows:
                wr.writerow(row)


class OracleCleaner(YamlLoader):
    def __init__(self):
        super(OracleCleaner, self).__init__()

    def issue_sqlplus_command(self, host_name, database_name, command):
        """ Issue a sqlplus command on the host, after sourcing the given database's variables """
        database = self.oracle_servers[host_name]['databases'][database_name]
        ipaddress = self.oracle_servers[host_name]['ipaddress']
        home = database['oracle_home']
        sid = database['oracle_sid']
        try:
            password = database['oracle_pass']
        except KeyError:
            password = '12!pass345'

        oracle_connection = OracleLib.OracleLib(ipaddress, sid=sid, home=home, password=password)
        r = oracle_connection.sqlplus(command)
        print(r)

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
                        cprint('- - WARNING: invalid diag dest: {0}'.format(diag_dest), 'red')
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

        # Verify that all expected DBs are running, and there are no extra DBs running
        accepted_dbs = ['+ASM1', '+ASM', '-MGMTDB']
        expected_sids = [database['oracle_sid'] for k, database in self.oracle_servers[host_name]['databases'].items()]
        extra_dbs = [sid for sid in databases if sid not in expected_sids and sid not in accepted_dbs]
        missing_dbs = [sid for sid in expected_sids if sid not in databases]
        databases = [database for database in databases if database not in accepted_dbs]

        if missing_dbs:
            cprint('WARN: Databases are not running: {0}'.format(missing_dbs), 'red')
        if extra_dbs:
            cprint('WARN: Unknown Databases running: {0}'.format(extra_dbs), 'yellow')

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
