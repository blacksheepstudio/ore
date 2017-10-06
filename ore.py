#!/usr/bin/env python
import sys
import pprint
from lib.utils import HostInventoryCreator, ExecutionPlanner, CSVGenerator, \
    OracleCleaner, TestPlanner, UpgradeController, ScriptExecutor

# CLI


def print_help():
    """ Display on-screen list of CLI options """
    print('')
    print('*** Oracle Regression Environment Manager ***')
    print('')
    cprint('[TestPlan commands]', 'yellow'')
    print(' ore mkcsv: create blank testplan csv file')
    print(' ore mkinv: create RobotFramework inventory for hosts/appliances')
    print(' ore aliases: create rbc aliases file from executions.yml')
    print('')
    cprint('[Host connector upgrade commands]', 'green')
    print(' ore upgradehosts: upgrade host connectors according to testplan')
    print(' ore upgradehost <hostname> <branch>: upgrade a single host')
    print('')
    cprint('[Host info commands]', 'blue')
    print(' ore lshost <hostname>: gather host information from given host')
    print(' ore lshosts <hostname>: gather host information from all hosts')
    print('')
    cprint('[Host management commands]', 'left')
    print(' ore sqlplus <hostname> <database> <command>: issue sqlplus command')
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

        # Issue SQLPlus command in given database
        elif arg.lower() in ['sqlplus', 'sql']:
            if len(sys.argv) < 5:
                print('Format: ore sqlplus <hostname> <database> <command>')
            else:
                hostname = sys.argv[2]
                dbname = sys.argv[3]
                command = sys.argv[4]
                oc.issue_sqlplus_command(hostname, dbname, command)

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
