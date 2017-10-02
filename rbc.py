"""
RBC will execute robot framework tests based on aliases in the aliases file

Example invocation:
    python rbc.py <alias name>

Here is an example of an aliases file with two aliases in it.
    [alias name]
    <path to inventory file> <path to inventory file> <path to test>
    [another alias name]
    <path to inventory file>:<prepend> <path to another inventory>:<prepend> <path to test>

Here is an example using actual values:
    [sun05-oracle-test]
    inv/host/sun05.py:rac1 inv/host/sun05.py:rac2 suites/orarac1+2/logsmart_mounts1.robot
"""

import os
import sys
import collections
import datetime
import re
import yaml
__author__ = 'Leif Taylor'


class SettingsLoader(object):
    def __init__(self):
        settings = yaml.load(open('yaml/rbc_settings.yml'))
        for k, v in settings.items():
            setattr(self, k, v)


class AliasParser(object):
    def __init__(self):
        self.settings = SettingsLoader()
        self.aliases_file = self.settings.aliases_file

        # Create dictionary of aliases
        self.aliases = self.read_aliases()

    def read_aliases(self):
        # Read all lines from aliases file into a list
        with open(self.aliases_file, 'r') as f:
            line_list = [line.replace('\n', '') for line in f.readlines() if line and not line.startswith('#')]
            f.close()
        base_dict = collections.OrderedDict()
        line_list = [line for line in line_list if line]

        # Create dictionary where each [alias_name] in aliases file is the key, and all lines under it are value list
        sections, indices = [], []
        for i, line in enumerate(line_list):
            match = re.search(r"\[([A-Za-z0-9_\-]+)\]", line)
            if match:
                sections.append(match.group(1))
                indices.append(i)
        for i, number in enumerate(indices):
            if i + 1 == len(indices):
                base_dict[sections[i]] = line_list[number + 1:]
            else:
                base_dict[sections[i]] = line_list[number + 1:indices[i + 1]]
        return base_dict

    def generate_command(self, alias):
        """
        Generate command from an alias in the aliases file.
        The input alias should look like:
        [alias_name]
        <path/to/inventory.py> <path/to/another.py:host> ... -v <somevariable:somevalue> ... <path/to/test.robot>

        The output command will look like:
        'docker run -i -v /path/to/local/framework3:/home/testing
        -v /path/to/local/inv:/home/testing/robot/inv brianwilliams/framework3
        robot -d . --log alias_name.html --output alias_name.xml -V path/to/inventory.py .......'

        :param alias: alias name (e.g. 'filesystem_test')
        :return: list of robot framework execution commands using given alias
        """
        try:
            if len(self.aliases[alias]) > 1:
                # If alias contains multiple test executions (to be run in parallel)
                return [self._generate_command(alias, i, '_{0}'.format(i)) for i in range(0, len(self.aliases[alias]))]
            else:
                # If alias is a single test execution
                return [self._generate_command(alias, 0)]
        except KeyError:
            print('No alias exists with name {0}'.format(alias))
            print('list of alias names: {0}'.format(self.aliases.keys()))
            quit()

    def _generate_command(self, alias, index, append=''):
        # Get entire raw line from alias, and split into sections for parsing
        line = self.aliases[alias][index]
        sections = line.split()

        # Create base command clause (enter docker container and run robot framework within)
        base_command = self.settings.drobot_command.replace(
            '<HTMLFILE>', alias + append + '.html').replace('<XMLFILE>', alias + append + '.xml')

        # Update directory settings in drobot command:
        base_command = base_command.replace('<framework3_dir>', self.settings.framework3_dir)
        base_command = base_command.replace('<inv_dir>', self.settings.inv_dir)
        base_command = base_command.replace('<docker_repo>', self.settings.docker_repo)

        # Get inventory clauses, and variable clauses
        variables = []
        inventory = []
        for i, item in enumerate(sections):
            variable_clause = re.match(r'([^=]+)=([^=]+)', item)
            # If entry is formed as name=value , assume it's a -v clause
            if variable_clause:
                variables.append('-v {0}:{1}'.format(variable_clause.group(1), variable_clause.group(2)))
            # If entry isn't the last entry, assume it's an inventory file
            elif i + 1 != len(sections):
                inventory.append('-V {0}'.format(item))
        variables = ' '.join(variables)
        inventory = ' '.join(inventory)

        # Get robot test file clause (should be last entry in alias)
        test = sections[-1]

        # Create final command to be issued, and remove any extra white space that may have sneaked in there
        command = re.sub(' +', ' ', '{0} {1} {2} {3}'.format(base_command, inventory, variables, test))
        return command

    def print_commands(self):
        """ Prints out actual docker robot commands for all aliases """
        for aliasname in self.aliases.keys():
            print('[{0}]'.format(aliasname))
            print(self.generate_command(aliasname))


class TestRunner(object):
    def __init__(self):
        self.ap = AliasParser()
        self.settings = SettingsLoader()

    def run_test(self, alias, date='', combine_logs=True):
        """ Run given alias, if alias is multi-line, will run all lines in parallel """
        log_dir = self.settings.log_dir

        commands = self.ap.generate_command(alias=alias)
        if not date:
            date = str(datetime.datetime.now()).split()[0]

        if len(commands) < 2:
            command = '{0} | tee {1}/{2}.txt'.format(commands[0], log_dir, alias)
            os.system(command)
            # Move log to log directory
            if self.settings.auto_archive_logs:
                self.move_logs(alias=alias)
        else:
            processed_commands = []
            for i, command in enumerate(commands):
                processed_commands.append('{0} | tee {1}/{2}_{3}.txt'.format(command, log_dir, alias, i))
            chain = ' & '.join(processed_commands)
            final_command = '{0}; wait'.format(chain)
            os.system(final_command)
            # Move logs to log directory
            if self.settings.auto_archive_logs:
                for i in range(0, len(commands)):
                    self.move_logs(alias='{0}_{1}'.format(alias, i), date=date)
                if combine_logs:
                    self.combine_logs('execution', date)
        return date

    def move_logs(self, alias, date=''):
        """ After test execution, move html, xml, and console output txt to dated log archive dir"""
        framework3_dir = self.settings.framework3_dir
        log_dir = self.settings.log_dir
        
        if not date:
            date = str(datetime.datetime.now()).split()[0]
        os.system('mkdir -p {0}/{1}'.format(log_dir, date))
        os.system('mv -f {0}/robot/{1}.html {2}/{3}'.format(framework3_dir, alias, log_dir, date))
        os.system('mv -f {0}/robot/{1}.xml {2}/{3}'.format(framework3_dir, alias, log_dir, date))
        os.system('mv -f {0}/{1}.txt {0}/{2}'.format(log_dir, alias, date))
        return date

    def combine_logs(self, log_name, date):
        """ Mount log directory to docker container, use rebot to combine logs """
        framework3_dir = self.settings.framework3_dir
        log_dir = self.settings.log_dir
        docker_repo = self.settings.docker_repo
        
        log_directory = '{0}/{1}'.format(log_dir, date)
        os.system('docker run -i -v {0}:/home/testing -v {1}:/home/testing/robot/logs {2} rebot -d . --log'
                  ' combined.html --output combined.xml --name {3} '
                  'logs/*.xml'.format(framework3_dir, log_directory, docker_repo, log_name))
        os.system('mv -f {0}/robot/combined.html {1}/{2}'.format(framework3_dir, log_dir, date))
        os.system('mv -f {0}/robot/combined.xml {1}/{2}'.format(framework3_dir, log_dir, date))


def print_help():
    print('******* RBC 2.1 (Robot Controller) ********')
    print('')
    print('- execute test: python rbc.py <aliasname>')
    print('- execute multiple tests: python rbc.py <aliasname> <anotheralias> ...')
    print('- see full command: python rbc.py aliases')

if __name__ == '__main__':
    a = TestRunner()
    ap = AliasParser()

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.lower() in ['aliases', 'aliaslist', 'commands']:
            ap.print_commands()
        elif arg.lower() in ['-h', '--h', '-help', '--help']:
            print_help()
        else:
            # If multiple test aliases are passed in, run them all sequentially, otherwise just run given alias
            if len(sys.argv) > 2:
                for alias in sys.argv[1:]:
                    a.run_test(alias)
            else:
                a.run_test(sys.argv[1])
    else:
        print_help()
