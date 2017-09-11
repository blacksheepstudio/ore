"""
Author: Leif Taylor
This is a library of sqlplus commands that can be executed on a remote host.
These methods can be used as keywords in Robot Framework
"""
import paramiko
import logging
import re
import atexit
import os


class OracleLib(object):
    """
    Library of keywords which issue sqlplus commands on remote host and handle the output

    To instantiate in python:
    a = OracleLib('xx.xx.xx.xx', sid='mydb', home='path/to/oracle/home')

    To construct keywords, use:
    For issuing insert/delete/create/etc:   stdout, stderr, rc = self.sqlplus('your SQL command here;')
    For queries (select, show):             row_list = self.query('your SQL query here;')

    Reference environmental variables like ORACLE_SID, ORACLE_HOME, ORACLE_PATH with:
    self.env['sid'], self.env['home'], self.env['path']

    Naming Conventions:
    Verify_<Keyword Name> must return True or False
    """

    def __init__(self, ipaddress, username='oracle', password='12!pass345', port=22,
                 sid='', home='', path='', *args, **kwargs):
        # Delimiter used for parsing sqlplus queries
        self.delimiter = "MiLeD"
        # Oracle environment
        self.env = {'sid': sid,
                    'home': home,
                    'path': path}

        # Connection params
        self.ipaddress = ipaddress
        self.username = username
        self.password = password
        self.port = port

        # Dictionary of update commands
        self.connection_params = kwargs

        # Connect
        self.client = None

    def open_database(self, sid=''):
        """
        Attempts to open database and trouhbleshoot and retry if errors arise
        :param sid: ORACLE_SID
        :return:
        """
        try:
            self.sqlplus('alter database open;', sid=sid)
        except OracleError as e:
            if e.errorcode == 'ORA-01589':
                logging.info(
                    'Database cannot open normally, requires RESETLOGS')
                self.sqlplus('alter database open RESETLOGS;')

    def create_user(self, name, password, sid=''):
        """
        Creates a user with basic priveledges

        :param name: user name
        :param password: user password
        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return:
        """
        self.sqlplus("create user {0} identified by {1};\n"
                     "grant connect to {0};\n"
                     "grant unlimited tablespace to {0};\n"
                     "grant create table to {0};\n"
                     "select * from dual;".format(name, password), sid=sid)

    def create_tablespace(self, name, datafile, size='40', sid=''):
        """
        Creates a permanent tablespace from given name, and datafile path

        Runs sqlplus: CREATE TABLESPACE <name> DATAFILE '<datafile>'
        :param name: tablespace name
        :param datafile: 'path/to/datafile.ora'
        :param size: size in megabytes
        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return:
        """
        self.sqlplus("CREATE TABLESPACE {0} DATAFILE '{1}' SIZE {2}M ONLINE;".format(name, datafile, size),
                     sid=sid)

    def create_table_set_rows(self, tablename, rowcount, sid=''):
        """
        This method should be used for db/log backup verification to set rows in a table for
        later verifications.

        If the table does not exist, it is created, and the rows are set.
        If the table exists already, it is dropped, created again and the rows are set

        :param sid: if sid is passed in as a param, will switch oracle_sid temporarily for this command
        :param tablename: table to create
        :param rowcount: number of rows to set
        :return: datetime on host
        """
        # Delete table if exists
        self.do_drop_table(tablename, sid=sid)
        # Create generic table
        self.sqlplus('create table {0} (firstname varchar(30), lastname varchar(30));'.format(tablename),
                     sid=sid)

        # Concatenate sqlplus statement to add N rows:
        command = 'insert all\n'
        for i in range(0, int(rowcount)):
            command += "into {0} values ('name{1}', 'lastname{1}')\n".format(
                tablename, i)
        command += 'select * from dual;'

        # Issue command
        self.sqlplus(command, sid=sid)

        # Verify rows correctly added
        if self.verify_row_count(tablename, int(rowcount), sid=sid):
            # Return the time
            return self.get_time()
        else:
            raise RuntimeError(
                'Rows may not have been correctly added to database!')

    def drop_table(self, tablename, sid=''):
        """
        Deletes table, will return error if table does not exist

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :param tablename: table to delete
        :return:
        """
        self.sqlplus('drop table {0};'.format(tablename), sid=sid)

    def do_drop_table(self, tablename, sid=''):
        """
        Deletes table if it exists.  Will not raise error if table does not exist.

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :param tablename: table to delete
        :return:
        """
        try:
            self.drop_table(tablename, sid)
        except OracleError as e:
            if e.errorcode == 'ORA-00942':
                pass
            else:
                raise e

    def drop_user(self, name, sid=''):
        """
        Drops user of given name

        :param name: user name
        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return:
        """
        self.sqlplus("drop user {0};".format(name), sid=sid)

    def drop_tablespace(self, name, sid=''):
        """
        Drops tablespace of given name

        :param name: tablespace name to drop
        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return:
        """
        self.sqlplus("DROP TABLESPACE {0};".format(name), sid=sid)

    def delete_datafile(self, datafile, sid=''):
        """
        **WARNING: DESTRUCTIVE**
        Warning: This uses operating system to run 'rm -f <datafile>'

        Be careful that you are deleting the correct datafile, or the correct file in general.
        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :param datafile: path/to/datafile.ora
        :return:
        """
        if datafile in self.list_datafiles(sid=sid):
            logging.info('Datafile metadata in database')
        else:
            logging.info(
                'Datafile metadata NOT in database, does tablespace still exist?')
        self.cmd('rm -rf {0}'.format(datafile), sid=sid)

    def get_row_count(self, tablename, sid=''):
        """
        Returns integer row count value

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :param tablename: name of table
        :return: integer
        """
        count = self.query(
            'select count(*) from {0};'.format(tablename), sid=sid)[0]['COUNT(*)']
        return int(count)

    def get_database_size(self, sid=''):
        """
        This will return the size of the database in GB

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return: float (size in bytes)
        """
        # Purge recyclebin to prevent hanging on the dba_free_space query
        self.sqlplus('purge dba_recyclebin;', sid=sid)
        size = self.query("select (d.total + c.total) total from (select sum(bytes) total from v\$datafile) d, "
                          "(select sum(block_size*file_size_blks) total from v\$controlfile) c;")[0]['TOTAL']
        free_space = self.query("select sum(bytes) free from dba_free_space;")[0]['FREE']
        mdl_estimate = int(size) - int(free_space)
        return mdl_estimate

    def get_database_size_gb(self, sid=''):
        """ Returns database size in GB """
        return float(self.get_database_size(sid=sid)) / 1024 / 1024 / 1024

    def get_database_name(self, sid=''):
        """
        Returns the global database name

        :param sid:
        :return: database name, e.g. 'MYDB'
        """
        r = self.query('select name from v\$database;', sid=sid)
        return r[0]['NAME']

    def get_au_size(self, name, sid=''):
        """
        Returns allocation unit size (in MB) of given diskgroup.
        Note: This keyword will raise error if this is a non-asm instance
        Note: If verifying AU size of mounted instance, name will be like: ACT<SID> e.g. ACTMYDB

        :param name: diskgroup name, e.g. 'FRA'
        :param sid:
        :return: INT size in MB, e.g. 1
        """
        if not self.is_asm():
            raise RuntimeError('AU Size is only valid for ASM databases')
        r = self.query('select name, group_number, allocation_unit_size/1024/1024, TYPE '
                       'from v\$asm_diskgroup where name=\'{0}\';'.format(name), sid=sid)
        try:
            return int(r[0]['ALLOCATION_UNIT_SIZE/1024/1024'])
        except IndexError:
            raise RuntimeError('Diskgroup {0} not found!'.format(name))

    def list_diskgroups(self):
        """
        Returns a list of all ASM diskgroups on host

        :return: list like ['DATA', 'FRA', 'OCR']
        """
        if self.is_asm():
            r = self.query("select name from v\$asm_diskgroup")
            return [dg['NAME'] for dg in r]
        else:
            raise RuntimeError('Diskgroups only valid on ASM Database')

    def grant_user(self, name, clause, sid=''):
        """
        Grant user given clause

        e.g.
        clause = 'create table'
        the command will be: 'grant create table to <name>'
        :param name: user name to be granted
        :param clause: priveledge to grant, e.g. 'create table'
        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return:
        """
        self.sqlplus('grant {0} to {1};'.format(clause, name), sid=sid)

    def get_oracle_sid(self):
        """
        This keyword is for debugging, to confirm oraclelib has the correct oracle_sid.

        Will return the current oracle_sid that is exported.  To change oracle_sid, use 'change_database()'
        :return: oracle_sid in self.oracle_env
        """
        return self.query('select instance_name from v\$instance')[0]['INSTANCE_NAME']

    def list_datafiles(self, sid=''):
        """
        This keyword returns the dba_datafile paths/names

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return: list of dba_datafile paths/names
        """
        dict_list = self.query('select file_name from dba_data_files;', sid)
        return [item['FILE_NAME'] for item in dict_list]

    def list_tablespaces(self, sid=''):
        """
        Returns list of tablespaces

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return:
        """
        tablespace_dict = self.query(
            'select tablespace_name from dba_tablespaces;', sid=sid)
        return [item['TABLESPACE_NAME'] for item in tablespace_dict]

    def list_users(self, sid=''):
        """
        List all users for this database

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return: list of users
        """
        dict_list = self.query('select username from dba_users;', sid)
        return [item['USERNAME'] for item in dict_list]

    def find_tablespace(self, name='', sid=''):
        """
        Return list of dictionaries with tablespace data, if name parameter supplied, will return only
        entry with that tablename.

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :param name: tablespace name (optional)
        :return: list of dictionaries
        """
        if name:
            tablespace_info = self.query('SELECT FILE_NAME,TABLESPACE_NAME,BYTES,AUTOEXTENSIBLE,MAXBYTES,INCREMENT_BY '
                                         'FROM DBA_DATA_FILES WHERE tablespace_name=\'{0}\';'.format(
                                             name.upper()),
                                         sid=sid)
            if tablespace_info:
                return tablespace_info
            raise RuntimeError(
                'No results found for tablespace named: {0}'.format(name.upper()))
        else:
            return self.query('SELECT FILE_NAME,TABLESPACE_NAME,BYTES,AUTOEXTENSIBLE,MAXBYTES,INCREMENT_BY '
                              'FROM DBA_DATA_FILES', sid=sid)

    def is_asm(self, sid=''):
        """
        This keyword returns True if the database is an ASM rac, and false if it is a filesystem

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return: True or False
        """
        asm_diskgroup_count = self.query("select count(name) from gv\$datafile where name like '+%'")[0]['COUNT(NAME)']
        return int(asm_diskgroup_count) > 0

    def db_verifications(self, sid=''):
        """
        Set of standard verifications to make sure Oracle Database is online, mounted, open, archivemode, and running.

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return: will raise error if verifications do not pass
        """
        if not self.verify_database_open(sid):
            raise RuntimeError('Database not open for read write')
        if not self.verify_archivelog_mode(sid):
            raise RuntimeError('Database not in archivelog mode')
        if not self.verify_instance_running(sid):
            raise RuntimeError('Pmon is not running. DB Instance down')

    def verify_table_exists(self, tablename, sid=''):
        """
        Verifies given table exists

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :param tablename: name of table to check for
        :return: True / False
        """
        try:
            self.query('select * from {0};'.format(tablename), sid=sid)
        except OracleError as e:
            if e.errorcode == 'ORA-00942':
                return False
            else:
                raise e
        return True

    def verify_log_directory_on_asm_diskgroup(self, sid=''):
        """
        Verifies that log destination (db_recovery_file_dest) is on the ASM diskgroup
        If this database is a filesystem database, this keyword will most certainly return False
        :return: True / False
        """
        if not self.is_asm():
            logging.warn(
                'This is a filesystem database, there is no asm diskgroup')
        r = self.query('show parameter db_recovery_file_dest;', sid)
        location = r[0]['VALUE']
        if '+' not in location:
            return False
        else:
            return True

    def verify_tablespace_exists(self, name, sid=''):
        """
        Verifies that the given tablespace exists.

        :param name: tablespace name
        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return:
        """
        try:
            self.find_tablespace(name=name, sid=sid)
        except RuntimeError:
            return False
        return True

    def verify_datafile_exists(self, datafile):
        """
        Verifies that given file exists on host.

        :param datafile: 'path/to/datafile.ora'
        :return: True or False
        """
        try:
            self.cmd('ls {0}'.format(datafile))
            return True
        except RuntimeError:
            return False

    def verify_database_active(self, sid=''):
        """
        Verifies that DATABASE_STATUS column in v$instance is ACTIVE

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return: True or False
        """
        r = self.query("select database_status from v\$instance", sid)
        if r[0]['DATABASE_STATUS'] == 'ACTIVE':
            return True
        else:
            return False

    def verify_sid_in_tnsnames(self, sid=''):
        """
        Verifies that Oracle SID is in $ORACLE_HOME/network/admin/tnsnames.ora

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return: True or False
        """
        if sid is None:
            return False
        if sid:
            actual_sid = sid
        else:
            actual_sid = self.env['sid']
        if 'CYGWIN' in self.os_type():
            home_dir = '\\\\'.join(self.env['home'].split('\\'))
            tnsdir = '{0}\\\\NETWORK\\\\ADMIN\\\\tnsnames.ora'.format(home_dir)
        else:
            tnsdir = '{0}/network/admin/tnsnames.ora'.format(self.env['home'])
        try:
            r = self.cmd('grep -i {0} {1}'.format(actual_sid, tnsdir))
            logging.debug('Tns grep result:\n{0}'.format(r))
        except RuntimeError:
            # Try again incase it is a rac instance with a rac instance name
            # (shave off last number)
            try:
                actual_sid = actual_sid[:-1]
                r = self.cmd('grep -i {0} {1}'.format(actual_sid, tnsdir))
                logging.debug('Tns grep result:\n{0}'.format(r))
            except RuntimeError:
                return False
        if r:
            return True

    def verify_database_open(self, sid=''):
        """
        Verifies database is open for read and write

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return: True / False
        """
        r = self.query('select open_mode from v\$database;', sid)
        if r[0]['OPEN_MODE'] == 'READ WRITE':
            return True
        else:
            return False

    def verify_database_mounted(self, sid=''):
        """
        Verifies database is mounted

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return: True / False
        """
        r = self.query('select open_mode from v\$database;', sid)
        if r[0]['OPEN_MODE'] == 'MOUNTED':
            return True
        else:
            return False

    def verify_archivelog_mode(self, sid=''):
        """
        Verifies that archivelog mode is enabled

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return: True / False
        """
        r = self.query('select log_mode from v\$database;', sid)
        if r[0]['LOG_MODE'] == 'ARCHIVELOG':
            return True
        else:
            return False

    def verify_snapshot_controlfile_on_asm_diskgroup(self, sid=''):
        """
        If database is ASM instance, control file must be in a diskgroup, not on the filesystem.

        If this verification is run against a filesystem database, will automatically return True,
        even though in reality the controlfile is on the filesystem.
        :return: True or False
        """
        if self.is_asm(sid=sid):
            stdout, __, __ = self.rman_cmd('show all;', sid=sid)
            for line in stdout:
                if 'CONFIGURE SNAPSHOT CONTROLFILE NAME TO' in line:
                    match = re.search("'.*?'", line)
                    if match:
                        if '+' in match.group(0):
                            return True
                        else:
                            return False
                    else:
                        raise RuntimeError(
                            'Could not find snapshot controlfile name')
            raise RuntimeError(
                'Could not find CONFIGURE SNAPSHOT CONTROLFILE line')
        else:
            logging.debug(
                'This database is a filesystem (non asm) returning True')
            return True

    def verify_instance_running(self, sid=''):
        """
        Verifies pmon is running

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return: True / False
        """
        # If SID Is passed in, use that, otherwise use the default sid
        if sid:
            oracle_sid = sid
        else:
            oracle_sid = self.env['sid']
        if 'CYGWIN' not in self.os_type():
            stdout, __, __ = self.cmd('ps -ef | grep pmon')
        else:
            stdout, __, __ = self.cmd(
                'sc qc OracleService{0}'.format(oracle_sid))
        if stdout:
            for item in stdout:
                if oracle_sid.lower() in item.lower():
                    return True
        return False

    def get_pid(self, sid=''):
        """
        Returns PID of current sid, unless sid is provided.

        If sid is provided, and process does not exist, will raise error

        :param sid: (optional) if provided will return PID of given sid
        :return: integer
        """
        oracle_sid = sid if sid else self.env['sid']
        if 'CYGWIN' in self.os_type():
            raise RuntimeError('Keyword not compatible with Windows host')
        else:
            stdout, _, __ = self.raw_cmd('ps -ef | grep [p]mon| grep {0}'.format(oracle_sid))
            if not stdout:
                raise RuntimeError('Process for {0} not found'.format(oracle_sid))
            pid = stdout[0].split()[1]
            return pid

    def kill_database_process(self, sid):
        """
        Idempotently kills running database process if it is running.
        Warning: This keyword is designed specifically to kill ghost scrub db process. Do not use for any other purpose.

        :param sid: sid of db process to kill
        :return:
        """
        # To protect user from killing their primary sid
        if sid == self.env['sid']:
            raise RuntimeError("I'm sorry Dave. I can't let you do that! (Cannot kill process of primary DB)")
        try:
            pid = self.get_pid(sid)
        except RuntimeError:
            return
        logging.info('Ghost DB: {0} found!'.format(sid))
        self._kill_process(pid)

    def _kill_process(self, pid):
        """
        Kills given process id. Will raise error if process not found.

        :param pid: process id
        :return:
        """
        stdout, stderr, rc = self.raw_cmd('kill -9 {0}'.format(pid))
        if rc != 0:
            raise RuntimeError('Kill process failed: {0}'.format(stderr))

    def verify_listener_active(self):
        """
        Verifies that tnslistener service is running

        :return: boolean
        """
        try:
            self.cmd('export ORACLE_HOME={0};{0}/bin/lsnrctl status'.format(self.env['home']))
        except RuntimeError:
            return False
        return True

    def start_listener(self):
        """
        Starts the tnslistener service

        :return:
        """
        self.cmd('export ORACLE_HOME={0};{0}/bin/lsnrctl start'.format(self.env['home']))

    def stop_listener(self):
        """
        Stops the tnslistener service

        :return:
        """
        self.cmd('export ORACLE_HOME={0};{0}/bin/lsnrctl stop'.format(self.env['home']))

    def verify_sid_in_oratab(self, sid=''):
        """
        Verifies that database is listed in oratab, on windows system, just checks that the process is running

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return: True or False
        """
        if sid:
            oracle_sid = sid
        else:
            oracle_sid = self.env['sid']

        if 'SunOS' in self.os_type():
            r = self.cmd('cat /var/opt/oracle/oratab')
        elif 'CYGWIN' in self.os_type():
            # TODO: There is no oratab in windows. I check process running
            # instead.
            return self.verify_instance_running(sid)
        else:
            r = self.cmd('cat /etc/oratab')
        for line in r[0]:
            if oracle_sid in line:
                return True
        # Maybe the sid is a rac instance, in which case let's remove the
        # number at the end and try again
        if self.is_asm():
            for line in r[0]:
                if oracle_sid[:-1] in line:
                    return True
        return False

    def verify_row_count(self, tablename, rows, sid=''):
        """
        Verifies that the given table has the correct amount of rows

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :param tablename: name of table in database
        :param rows: amount of rows expected in table
        :return: True / False
        """
        count = self.get_row_count(tablename=tablename, sid=sid)
        logging.info('Table: {0}, Expecting {1} rows, found {2}'.format(
            tablename, rows, count))
        return count == int(rows)

    def shutdown_immediate(self, sid=''):
        """
        Issues 'shutdown immediate;' command

        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return:
        """
        self.sqlplus('SHUTDOWN IMMEDIATE;', sid=sid)

    # The uncommented startup was being used, but has very different functionality
    # def startup(self, sid=''):
    #     """
    #     Attempts to startup and open the database and troubleshoot and re-attempt if startup fails.
    #     :param sid: oracle_sid to use
    #     :return:
    #     """
    #     try:
    #         self.sqlplus('startup;', sid=sid)
    #     except OracleError as e:
    #         if e.errorcode == 'ORA-01589':
    #             logging.info('Database cannot open normally, requires RESETLOGS')
    #             self.sqlplus('alter database open RESETLOGS;')

    def startup(self, clause='', sid=''):
        """
        Issues 'startup;' or if clause given 'startup <clause>;'

        :param clause: clause like 'NO MOUNT' or 'NO RESETLOGS'
        :param sid: If passed in as a parameter, will connect to that oracle_sid for this command
        :return:
        """
        if clause:
            self.sqlplus('STARTUP {0};'.format(clause), sid=sid)
        else:
            self.sqlplus('STARTUP;', sid=sid)

    def alter_database(self, clause, sid=''):
        """
        Issues 'alter database <clause>;'

        :param clause: like 'OPEN' or 'MOUNT'
        :param sid: If passed in as a parameter, will connect to that oracle database for this command
        :return:
        """
        self.sqlplus('ALTER DATABASE {0};'.format(clause), sid=sid)

    def run_rman_backup(self, time, directory='/home/oracle', filename=''):
        """
        Run an rman backup

        :param time: backup will capture all changes from sysdate - 'time' (in hours).
        :param directory: target directory for rman backup data e.g. /home/oracle
        :param filename: filename to give to rman backup
        :return: backup filename
        """
        self.cmd('mkdir -p {0}'.format(directory))

        # If filename parameter not supplied, will generate unique backupname
        if not filename:
            filename = '%U'
        stdout, stderr, rc = self.rman_cmd('run {{allocate channel c1 device type disk format \'{0}/{1}\'; '
                                           'backup archivelog from time \'sysdate - {2}\' force;'
                                           ' release channel c1;}}'.format(directory, filename, time))
        for line in stdout:
            if 'piece handle=' in line:
                return line.split('piece handle=')[1].split()[0]

    # DB and Unit Tests
    def test_database(self, sid=''):
        print('Verifications on {0}, IP: {1}'.format(sid, self.ipaddress))
        tests = [self.verify_archivelog_mode, self.verify_database_active,
                 self.verify_instance_running, self.verify_database_open,
                 self.verify_sid_in_oratab, self.verify_sid_in_tnsnames]
        for method in tests:
            print('Test: {0}, Result: {1}'.format(
                method.__name__, method(sid=sid)))

    def _test_all(self, sid=''):
        """
        Tests a large handful of methods in OracleLib

        :param sid: if given as a param will use this oracle sid instead of default
        :return: will raise error if method fails
        """
        print('Oracle SID: {0}'.format(self.get_oracle_sid()))
        print('DB Size: {0}'.format(self.get_database_size(sid)))
        print('Data files: {0}'.format(self.get_datafiles(sid)))
        print('Is asm: {0}'.format(self.is_asm(sid)))
        print('Active: {0}'.format(self.verify_database_active(sid)))
        print('Read Write: {0}'.format(self.verify_database_open(sid)))
        print('Mounted (not read write): {0}'.format(
            self.verify_database_mounted(sid)))
        print('Archivelog Mode: {0}'.format(self.verify_archivelog_mode(sid)))
        print('Created 100 rows at time: {0}'.format(
            self.create_table_set_rows('unittesttable', 100, sid)))
        print('Actual row count: {0}'.format(
            self.get_row_count('unittesttable', sid)))
        print('Dropping Table')
        self.drop_table('unittesttable', sid)
        print('Table still exists: {0}'.format(
            self.verify_table_exists('unittesttable', sid)))
        print('Idempotently dropping already dropped table')
        self.do_drop_table('unittesttable', sid)
        print('Unit tests all passed')

    # Oracle Environment / Parsing and SQLPlus low level commands

    def _env_status_check(self):
        sid = self.env['sid']
        home = self.env['home']
        path = self.env['path']
        # Attempt to find Oracle environmental variables using SID if not
        # provided
        if sid and home and path:
            logging.debug(
                'Oracle Environment: sid: {0}, home: {1}, path: {2}'.format(sid, home, path))
        elif sid and not home and not path:
            self.env['home'], self.env[
                'path'] = self.determine_oracle_environmental_variables(sid)
        elif sid and home and not path:
            self.env['path'] = '{0}/bin'.format(home)
        elif not sid and not home and not path:
            raise RuntimeError('Must provide sid, or sid and oracle home, or sid, home, and path\n'
                               'e.g. a = OracleLib("172.27.17.125",'
                               ' sid="mydb", home="/product/oracle/db_1"')

    def determine_oracle_environmental_variables(self, sid):
        """
        Attempts to find oracle home and oracle path directories using SID to search for init<sid>.ora

        :param sid: ORACLE_SID e.g. mydb1
        :return: oracle_home, oracle_path
        """
        if 'CYGWIN' in self.os_type():
            raise RuntimeError(
                'Cannot determine environmental variables on Cygwin')
        else:
            # TODO: More robust method of finding would be to parse oratab, remember HPUX is in /var/opt/oracle/
            # Find Oracle_Home directory by searching for database init or
            # spfile
            stdout, stderr, rc = self.cmd("find / -type f -name 'init{0}.ora' 2>/dev/null".format(sid),
                                          raise_error=False)
            if not stdout:
                # If init.ora not found, search for spfile
                stdout, stderr, rc = self.cmd("find / -type f -name 'spfile{0}.ora' 2>/dev/null".format(sid),
                                              raise_error=False)
                if not stdout:
                    # If neither spfile nor init.ora found, raise error
                    raise RuntimeError(
                        'Could not determine oracle env, please provide SID, home and path')
                orahome = stdout[0].replace(
                    '/dbs/spfile{0}.ora'.format(sid), '')
            else:
                orahome = stdout[0].replace('/dbs/init{0}.ora'.format(sid), '')

            # Set oracle_path to orahome/bin
            orapath = '{0}/bin'.format(orahome)
        return orahome, orapath

    def change_database(self, new_sid, auto_correct=True):
        """
        Changes the SID of the env dictionary in OracleLib.

        All keywords will now act on the database_sid that you have changed to.

        Note:
        Because mounted child instances can have numbers appended to them, auto_correct
        will attempt to find the new child sid even if you have forgotten to add an append.
        e.g. if you enter 'achild' as your sid, but the actual database sid is 'achild1'

        :param new_sid: oracle_sid to change to
        :param auto_correct: automatically determine sid name, e.g. 'achild' is actually 'achild1'
        :return: actual new oracle_sid of running instance
        """
        stdout, stderr, rc = self.cmd(
            'ps -ef | grep pmon | grep {0} | grep -v grep'.format(new_sid))
        if not stdout:
            raise RuntimeError('No SID found, is instance running?')
        # Search ps output for running oracle instance with new_sid name
        if auto_correct:
            for line in stdout:
                if new_sid in line:
                    actual_sid = line.split('ora_pmon_')[-1]
                    self.env['sid'] = actual_sid
                    return actual_sid
        else:
            self.env['sid'] = new_sid
        # If new oracle_sid not found, or instance not running
        raise RuntimeError(
            'Oracle_SID: {0} not found, or instance not running'.format(new_sid))

    def rman_cmd(self, command, sid='', ignore_env=False, raise_error=True, **kwargs):
        """
        Sources environmental variables and launches a command with 'rman target /'

        :param command:
        :param sid:
        :return:
        """
        # Find oracle environment if not already found
        self._env_status_check()

        # Change sid if sid is passed in as param
        if sid:
            old_sid = self.env['sid']
            self.env['sid'] = sid

        # Raise error if oracle env not initialized and ignore_env is set to
        # False
        if not ignore_env and not self.env:
            raise RuntimeError('No oracle environment')

        oracle_exports = self._create_export_string()

        # Issue concatinated one line command which exports variables, opens sqlplus, and issues a sqlplus statement
        # final_command = oracle_exports + ';' + 'echo "' + command + '" | sqlplus -S / as sysdba'
        final_command = '{0};echo "{1}" | rman target /'.format(
            oracle_exports, command)

        logging.debug('Connecting to database: {0}'.format(self.env['sid']))
        logging.debug(
            'Issuing SQLPlus command from bash:\n{0}'.format(final_command))
        stdout, stderr, rc = self.cmd(final_command)

        # Change sid back to default if sid was passed in
        if sid:
            self.env['sid'] = old_sid

        # Check for RMAN errors and return
        if raise_error:
            self.raise_for_error(stdout)
        return stdout, stderr, rc

    def sqlplus_cmd(self, command, sid, ignore_env=False, raise_error=True, **kwargs):
        """
        Export Oracle_Home, SID, and Path, open sqlplus session as sysdba, and issue 'command'

        :param command: sql statement
        :param user: (optional) will issue command as given user
        :param password: (optional) password for given user
        :param sid: if sid is passed in, will change oracle_sid temporarily to run command
        :param ignore_env: default False, if True will attempt to launch sqlplus if no env variables are given
        :param kwargs:
        :return:
        """
        # Find oracle environment if not already found
        self._env_status_check()

        # Change sid if sid is passed in as param
        if sid:
            old_sid = self.env['sid']
            self.env['sid'] = sid

        # Raise error if oracle env not initialized and ignore_env is set to
        # False
        if not ignore_env and not self.env:
            raise RuntimeError('No oracle environment')

        oracle_exports = self._create_export_string()

        # Issue concatinated one line command which exports variables, opens sqlplus, and issues a sqlplus statement
        # final_command = oracle_exports + ';' + 'echo "' + command + '" | sqlplus -S / as sysdba'
        if 'user' in kwargs:
            user, password = kwargs['user'], kwargs['password']
            final_command = '{0};echo "{1}" | sqlplus -S {2}/{3} as sysdba'.format(oracle_exports,
                                                                                   command, user, password)
        else:
            final_command = '{0};echo "{1}" | sqlplus -S / as sysdba'.format(
                oracle_exports, command)
        logging.debug('Connecting to database: {0}'.format(self.env['sid']))
        logging.debug(
            'Issuing SQLPlus command from bash:\n{0}'.format(final_command))
        stdout, stderr, rc = self.cmd(final_command)

        # Change sid back to default if sid was passed in
        if sid:
            self.env['sid'] = old_sid

        # Check for ORA or SP2 error messages and return
        if raise_error:
            self.raise_for_error(stdout)
        return stdout, stderr, rc

    def _create_export_string(self):
        """
        Creates export variable string like:

        export PATH=blah; export ORACLE_HOME=blah; export ORACLE_SID=blah;
        OR
        if a windows host will put exports into a script, and then source them
        :return: oracle exports command
        """
        # Create string which exports environmental variables from OracleEnv
        # class ()
        if 'CYGWIN' not in self.os_type():
            # If NOT Cygwin, concatenate environmental variable exports
            method = 'export'
            oracle_exports = '{0} PATH={1}:$PATH;' \
                             '{0} ORACLE_HOME={2};' \
                             '{0} LD_LIBRARY_PATH={2}/lib;' \
                             '{0} ORACLE_SID={3}'.format(method, self.env['path'], self.env['home'],
                                                         self.env['sid'])
        else:
            # If Cygwin, need to source environmental variables for shell session from script
            # TODO: May need to get Oracle Home and Path as well for some
            # systems.
            self.cmd(
                'echo "export ORACLE_SID={0}" > /tmp/sid'.format(self.env['sid']))
            oracle_exports = 'source /tmp/sid'
        return oracle_exports

    def sqlplus(self, command, sid='', **kwargs):
        """
        Issue a mysql command

        Will raise/return Oracle errors
        :param command: e.g 'INSERT INTO mytable VALUES (30, 22, 15)'
        :param sid: if sid is passed in, will change oracle_sid temporarily to run command
        :param args:
        :param kwargs:
        :return: stdout, stderr, rc
        """
        # TODO: Instead of just adding 1 at the end, search processes to find similiar sid if given sid doesn't work
        # Fix if there is a double ;; in any part of the command
        command = re.sub(';+', ';', command)
        logging.debug(
            'Issuing command with sid {0}:\n{1}'.format(sid, command))

        if 'CYGWIN' in self.os_type():
            try:
                stdout, stderr, rc = self.sqlplus_cmd(command, sid, **kwargs)
            except RuntimeError:
                try:
                    logging.debug(
                        'Sid: {0} not found, trying Sid: {0}1'.format(sid))
                    stdout, stderr, rc = self.sqlplus_cmd(
                        command, '{0}1'.format(sid))
                except RuntimeError:
                    raise RuntimeError('Oracle Instance not found')
        else:
            try:
                stdout, stderr, rc = self.sqlplus_cmd(command, sid, **kwargs)
            except OracleError as e:
                # ORA-01034 is instance not found error, ORA-12560 is windows
                # TNS: protocol adapter error
                if e.errorcode == 'ORA-01034' or e.errorcode == 'ORA-12560':
                    # If the SID was not found, add 1 to the end of it, in case
                    # it is a newly created asm instance
                    logging.debug(
                        'Sid: {0} not found, trying Sid: {0}1'.format(sid))
                    stdout, stderr, rc = self.sqlplus_cmd(
                        command, '{0}1'.format(sid))
                else:
                    raise e
        return stdout, stderr, rc

    def query(self, command, sid='', **kwargs):
        """
        Query Oracle database and return output as list of dictionaries where:
        list index is database row
        dictionary kv pairs are column/row pairs

        :param command: e.g. 'SELECT * FROM mytable;'
        :param sid: if sid is passed in, will change oracle_sid temporarily to run command
        :param args:
        :param kwargs:
        :return: list of dictionaries
        """
        # Add ';' if not already in command
        if command[-1] != ';':
            command += ';'

        # Add delimiter, line size, and pagesize to command for parsing
        # purposes, and then issue query
        command = 'set colsep "{0}"\nset linesize 32000\nSET PAGESIZE 50000\nset numwidth 49\n'.format(
            self.delimiter) + command
        stdout, __, __ = self.sqlplus(command, sid=sid, **kwargs)
        return self.parse_query(stdout)

    def parse_query(self, output):
        """
        Parse output sqlplus query into a list of dictionaries where each dictionary is a row of kv pairs

        :param output: output of sqlplus query
        :return: list of dictionaries
        """
        logging.debug(
            'Attempting to parse query response:\n{0}'.format(output))
        # Get Column Names and Find Rows in output
        column_list = []
        table_rows = []
        for i in range(0, len(output)):
            if output[i]:
                # Get column headers and strip whitespace
                column_list = output[i].split(self.delimiter)
                column_list = [item.strip() for item in column_list]
                # Get row values and strip whitespace
                unstripped_rows = [row.split(self.delimiter)
                                   for row in output[i + 2:-1]]
                # Each row is a list, and must have all of the strings within
                # it stripped
                for row in unstripped_rows:
                    # .replace to remove the \t automatically added if there are four spaces in entry
                    table_rows.append(
                        [item.strip().replace('\t', '    ') for item in row])
                break

        # Create list of dictionaries where each list index is a row, populated
        # by a dictionary with column/value pairs
        table_data = [dict(zip(column_list, row)) for row in table_rows]
        logging.debug('Parsed response:\n{0}'.format(table_data))
        # If empty response, return empty list
        if not table_data:
            return []
        if re.search('\d+ rows selected.', str(table_data[-1])):
            # If tagline at end of output "N rows selected" remove that from
            # the response and empty line it creates
            return table_data[:-2]
        else:
            return table_data

    def find_rac_instance(self, sid):
        """
        Returns the instance name from the given database name.

        Usually these will be the same, in the case that this is a rac node however,
            it may be named <sid>1, or <sid>2 etc.
        :param sid: Database name, e.g. rh66db
        :return: '<databasename><instance_number>', e.g. 'rh66db1'
        """
        # First check processes for instance name
        return self._instance_name_from_processes(sid)

    def _instance_name_from_processes(self, sid):
        """
        Parses ps output, or sc output, returns oracle instance from database name.

        :param sid: database name | e.g. 'rh66db'
        :return: actual instance name/oracle_sid  | e.g. 'rh66db1'
        """
        # TODO: Redo this parsing
        # In the case of non-windows host, use ps to find instance name
        if 'CYGWIN' not in self.os_type():
            return self._parse_ps_output(sid)
        # In the case of windows host, use sc to find instance name
        else:
            return self._parse_sc_output(sid)

    def _parse_ps_output(self, sid):
        """
        Internal method, parses ps_output and returns oracle instance name from the given database name

        :param sid: expected oracle_sid
        :return: actual instance oracle_sid
        """
        stdout, __, __ = self.cmd('ps -ef | grep pmon')
        logging.debug('Parsing ps for database like: {0}'.format(sid))
        logging.debug('ps result:\n{0}'.format(str(stdout)))
        match = re.search('ora_pmon_{0}(.+?)'.format(sid), str(stdout))
        if match:
            ora_pmon_orcsid = match.group(0).strip('\'')
            # Will get a string like ora_pmon_<instance_name>, return only the
            # instance name
            name = ora_pmon_orcsid.split('_')[2]
            if name == sid:
                logging.debug('Sid found: {0}'.format(sid))
                return sid
            else:
                if len(name) > len(sid):
                    if name[-1].isdigit():
                        logging.debug('ASM instance found: {0}'.format(name))
                        return name
                    else:
                        raise RuntimeError(
                            'Parsing is probably wrong. Returned {0}'.format(name))
                if len(name) <= len(sid):
                    raise RuntimeError(
                        'Parsing is probably wrong. Returned {0}'.format(name))
        else:
            raise RuntimeError(
                'Unable to find any instance starting with {0}'.format(sid))

    def _parse_sc_output(self, sid):
        """
        Internal method, parses sc output (windows) and returns running database instance name from the given
            database name.

        :param sid: expected oracle_sid
        :return: actual instance oracle_sid
        """
        stdout, __, __ = self.cmd('sc qc OracleService{0}'.format(sid))
        logging.debug(
            'Parsing sc processes for database like: {0}'.format(sid))
        logging.debug('sc qc output:\n{0}'.format(str(stdout)))
        match = re.search('OracleService{0}(.+?)'.format(sid), str(stdout))
        if match:
            ora_pmon_orcsid = match.group(0).strip('\'')
            # Will get a string like ora_pmon_<instance_name>, return only the
            # instance name
            name = ora_pmon_orcsid.split('OracleService')[1]
            if name == sid:
                logging.debug('Sid found: {0}'.format(sid))
                return sid
            else:
                if len(name) > len(sid):
                    if name[-1].isdigit():
                        logging.debug('ASM instance found: {0}'.format(sid))
                        return name
                    else:
                        raise RuntimeError(
                            'Parsing is probably wrong. Returned {0}'.format(name))
                if len(name) <= len(sid):
                    raise RuntimeError(
                        'Parsing is probably wrong. Returned {0}'.format(name))
        else:
            raise RuntimeError(
                'Unable to find any instance starting with {0}'.format(sid))

    def raise_for_error(self, response):
        """
        Searches stdout for ORA or SP2 (sqlplus) exceptions and raises for error
        """
        # TODO: Currently this cannot report both an ORA, and SP2 error if they
        # are in the same response
        output_string = ' '.join(response)
        logging.debug(
            'Searching for ORA or SP2 error in response:\n{0}'.format(response))
        if re.search('ORA-\d+', output_string):
            # Get error code searching for ORA-#####
            errorcode = re.search('ORA-\d+', output_string).group(0)
            # Extract error message from response (shave off ' :')
            errormessage = output_string.split(errorcode)[1].strip()[2:]
            raise OracleError(errorcode, errormessage)
        elif re.search('SP2-\d+', output_string):
            # Get error code searching for ORA-#####
            errorcode = re.search('SP2-\d+', output_string).group(0)
            # Extract error message from response (shave off ' :')
            errormessage = output_string.split(errorcode)[1].strip()[2:]
            raise SQLPlusError(errorcode, errormessage)
        elif re.search('RMAN-\d+', output_string):
            # Get error code searching for ORA-#####
            errorcode = re.search('RMAN-\d+', output_string).group(0)
            # Extract error message from response (shave off ' :')
            errormessage = output_string.split(errorcode)[1].strip()[2:]
            raise RMANError(errorcode, errormessage)
        else:
            return

    # Host (non oracle) commands:

    def get_time(self):
        """
        Gets the time in 'YYYY-MM-DD hr:mn:sc' on host

        :return: YYYY-MM-DD hr:mn:sc
        """
        out, err, rc = self.cmd('date +"%Y-%m-%d"\' \'"%T"')
        date = out[0]
        return date

    def os_type(self):
        """
        Returns the response string from the 'uname' command.

        :return: string
        """
        out, err, rc = self.cmd('uname')
        return out[0]

    # Path Correction / OS Handling Methods

    def correct_path(self, mnt_pnt):
        """
        Corrects path for os.

        -If os_type is Windows and a Linux like path is passed in, e.g. '/example', this method
        will return 'C:\\example'.
        -If the system isn't Windows, and a windows type path is passed in,
        this method will return a Linux type path, e.g. 'C:\\example' -> '/example'
        -If the correct path type for the OS is used, this method will just return the argument
        unchanged.
        :param mnt_pnt: a path like '/childmount' or 'C:\\childmount'
        :return: path string
        """
        # Determine OS type of host
        if 'CYGWIN' in self.os_type():
            platform = 'windows'
        else:
            platform = 'unix'

        # Verify mountpoint in proper format
        if '\\' in mnt_pnt and '/' in mnt_pnt:
            raise RuntimeError(
                'Mount point: {0} contains forward and backward slashes'.format(mnt_pnt))
        if '\\' not in mnt_pnt and '/' not in mnt_pnt:
            logging.debug('mnt_pnt: {0} contains no slashes'.format(mnt_pnt))
            if platform == 'windows':
                return 'C:\\\\{0}'.format(mnt_pnt)
            else:
                return '/{0}'.format(mnt_pnt)
        # Determine OS type of mountpoint given
        if '\\' in mnt_pnt:
            path_type = 'windows'
        elif '/' in mnt_pnt:
            path_type = 'unix'

        # Return if pathtype already matches os type
        if platform == path_type:
            return mnt_pnt
        else:
            # Convert Unix Style to Windows
            if platform == 'windows':
                # Shave off last character if '/'
                if mnt_pnt[-1] == '/':
                    mnt_pnt = mnt_pnt[:-1]
                # Convert Unix style directory to Windows
                return self.fix_path('C:{0}'.format(mnt_pnt.replace('/', '\\\\')))
            # Convert Windows Style to Unix
            else:
                # Split out any backslashes, creating a list of sub directories
                dir_list = [item for item in mnt_pnt.split('\\') if item]
                # Erase first entry in list (it will be 'C:' or 'E:' etc)
                dir_list = dir_list[1:]
                return self.fix_path('/{0}'.format('/'.join(dir_list)).replace('\x07', ''))

    def fix_path(self, path):
        """
        Makes sure given path string is formatted correctly

        :param path: a path string
        :return: corrected string (if needed)
        """
        path = os.path.normpath(os.path.expanduser(path))
        if path.startswith("\\"):
            return "C:" + path
        return path

    def parse_oratab(self, path='/etc/oratab'):
        """
        Parses oratab and returns database name and oracle home

        :param path: e.g. /etc/oratab
        :return: databasename, oracle_home
        """
        database_name = self.get_database_name()
        r = self.cmd('cat {0} | grep -i {1}'.format(path, database_name))
        return r[0][0].split(':')[0], r[0][0].split(':')[1]

    # Paramiko helper methods

    def connect(self):
        """
        Connect to remote host

        :return: paramiko SSHClient object
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.ipaddress, username=self.username, password=self.password,
                       port=self.port, **self.connection_params)
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

    def raw_cmd(self, command, ascii=False):
        """
        Issue direct command over ssh, does not raise for error
        :param command: command to issue
        :param ascii: Attempt to convert to ascii if true, if false return unicode
        :return: stdout (list of lines), stderr (list of lines), return code (integer)
        """
        if not self.client:
            self.client = self.connect()
        stdin, stdout, stderr = self.client.exec_command(command, timeout=60)
        stdin.close()
        if ascii:
            stdout_final = [line for line in stdout.read().splitlines()]
            stderr_final = [line for line in stderr.read().splitlines()]
        else:
            stdout_final = stdout.readlines()
            stderr_final = stderr.readlines()
        rc = stdout.channel.recv_exit_status()
        logging.debug('Return from raw_cmd:\n{0}\n{1}\n{2}'.format(
            stdout_final, stderr_final, rc))
        return stdout_final, stderr_final, rc

    def cmd(self, command, ascii=True, raise_error=True):
        """
        Issue direct command over ssh, with handlers, can raise for error and attempt to convert to ascii

        :param command:
        :param ascii:
        :param raise_error:
        :return: stdout (list of lines), stderr (list of lines), return code (integer)
        """
        stdout, stderr, rc = self.raw_cmd(command, ascii=ascii)
        if raise_error:
            if rc != 0:
                # If ascii set to false, error message will have u'<message>\n'
                raise RuntimeError(str(stderr) + 'with rc: ' + str(rc))
        return stdout, stderr, rc

    # Actifio Specific Keywords

    def issue_command_as_root(self, command, root_user='root', root_pass='12!pass345'):
        old_user, old_pass = self.username, self.password
        self.ssh_disconnect()
        try:
            self.username, self.password, = root_user, root_pass
            stdout, stderr, rc = self.raw_cmd(command)
        finally:
            self.ssh_disconnect()
            self.username, self.password = old_user, old_pass
        return stdout, stderr, rc

    def uninstall_connector(self):
        ostype = self.os_type()
        if ostype == 'SunOS':
            self._uninstall_connector_solaris()
        elif ostype == 'Linux':
            self._uninstall_connector_linux()
        elif ostype == 'AIX':
            self._uninstall_connector_aix()
        elif ostype == 'HP-UX':
            self._uninstall_connector_hpux()
        else:
            raise RuntimeError('I can\'t deal with this os: {0}'.format(ostype))

    # def install_connector(self):
    #     ostype = self.os_type()
    #     if ostype == 'SunOS':
    #         self._install_connector_solaris()
    #     elif ostype == 'Linux':
    #         self._install_connector_linux()
    #     elif ostype == 'AIX':
    #         self._install_connector_aix()
    #     elif ostype == 'HP-UX':
    #         self._install_connector_hpux()
    #     else:
    #         raise RuntimeError('I can\'t deal with this os: {0}'.format(ostype))

    def _uninstall_connector_solaris(self):
        # First create alternate admin file so that package can be removed without prompt
        self.issue_command_as_root("sed -e 's/action=ask/action=nocheck/g' "
                                   "/var/sadm/install/admin/default > /var/sadm/install/admin/default.new")
        # Now remove package non-interactively with alternate admin file
        self.issue_command_as_root("pkgrm -n -a /var/sadm/install/admin/default.new udsagent")

    def _uninstall_connector_linux(self):
        self.issue_command_as_root("rpm -e udsagent")

    def _uninstall_connector_hpux(self):
        self.issue_command_as_root("swremove udsagent")

    def _uninstall_connector_aix(self):
        self.issue_command_as_root("nstallp -u udsagent")
        
    # def _install_connector_solaris(self, gpg_location):
    #
    #
    # def _install_connector_linux(self):
    #     self.issue_command_as_root("rpm -e udsagent")
    #
    # def _install_connector_hpux(self):
    #     self.issue_command_as_root("swremove udsagent")
    #
    # def _install_connector_aix(self):
    #     self.issue_command_as_root("nstallp -u udsagent")
        
    def get_connector_version(self):
        """
        Returns connector version
        :return: connector version
        """
        try:
            stdout, __, __ = self.raw_cmd('cat /act/etc/key.txt')
            return stdout[0].rstrip('\n')
        except:
            return 'Connector: Cannot Determine, check /act/etc/key.txt exists?'

    def verify_backup_inband(self, jobname, root_user='root', root_pass='12!pass345'):
        """
        Parses UDSAgent.log and returns True if backup is in-band

        :param root_user: username with root priveledges
        :param root_pass: root user password for sudo
        :param jobname: e.g. Job_12345
        :return: True or False
        """
        # If image name passed in instead of job name
        if 'Image' in jobname:
            jobname = jobname.replace('Image', 'Job')

        stdout, __, __ = self.issue_command_as_root("cat /var/act/log/UDSAgent.log | grep -i '{0} oraclebackupmgr' "
                                                    "| grep -i DATAMOVEMENT=INBAND".format(
                                                        jobname),
                                                    root_user, root_pass)
        if stdout:
            return True
        else:
            return False

# Actifio Job verifications (rman log checks)

    def verify_numberofchannels(self, job, channels):
        """
        Verifies that given snapshot job used AT LEAST the given number of channels
        :param job: e.g. Job_12345
        :param channels: e.g. 4
        :return: True or False
        """
        # Subtract 1 from channels input because rman channels are 0 indexed
        channels = int(channels) - 1
        lines = self.get_rman_lines(job=job)
        channel_lines = [line for line in lines if 'channel d{0}'.format(channels) in line]
        if channel_lines:
            return True
        else:
            return False

    def verify_level0_backup(self, job, sid=None):
        """
        Verifies that the snapshot job ran was a level0 backup
        :param job: e.g. Job_12345
        :param sid: If not specified, will use OracleLib's current sid
        :return: True or False
        """
        if not sid:
            sid = self.env['sid']
        lines = self.get_rman_lines(job=job, sid=sid)
        matches = [line for line in lines if 'Level_0_Backup_Start' in line]
        if matches:
            return True
        else:
            return False

    def verify_job_in_log(self, job, location='/var/act/log'):
        """ Verifies that the given job is in the rman log """
        try:
            lines = self.get_rman_lines(location=location)
        except RuntimeError:
            logging.warn('Rman log not found in {0}'.format(location))
            return False
        job_dict = self.get_jobs_in_lines(lines)
        return job in job_dict.keys()

    def verify_au_size(self, name, size):
        """
        Verifies that the AU Size (in MB) of the given diskgroup is the expected size

        :param name: diskgroup name, e.g. 'DATA'
        :param size: size in MB, e.g. '1' or 1
        :return: True or False
        """
        actual_size = self.get_au_size(name)
        return str(actual_size) == str(size)

# Rman log parsing

    def get_rman_lines(self, job=None, sid=None, location='/var/act/log'):
        """
        Return list of all lines in rman log
        :param job: If specified, only returns lines pertaining to this job
        :param sid: If not specified, will use current sid OracleLib is using
        :param location: Specifies directory of rman log, you can also specify a path to specific rmanlog
        :return: list of lines in Rman log
        """
        if not sid:
            sid = self.env['sid']

        database_down = False

        # Get global database name (rman log will be named like 'mydb_rman.log')
        try:
            db_name = self.get_database_name(sid=sid).lower()
        except OracleError as e:
            if e.errorcode == 'ORA-01034':
                logging.info('Database instance is IDLE, using provided sid to determine '
                             'rman log name instead of querying global database name.')
                db_name = sid
                database_down = True
            else:
                raise e

        # Handles if location specified is a directory of log location, or log itself
        if '.log' in location:
            lines, __, __ = self.cmd('cat {0}'.format(location))
        else:
            try:
                lines, __, __ = self.cmd('cat {0}/{1}_rman.log'.format(location, db_name))
            except RuntimeError as e:
                if db_name[-1].isdigit() and database_down:
                    logging.warn('{0}_rman.log did not exist, db name provided has a digit as last character, '
                                 'this could indicate it is a node name. Rman logs are named like: '
                                 '<global database name>_rman.log ... Attempting to '
                                 'open rman log named {1}_rman.log'.format(db_name, db_name[:-1]))
                    lines, __, __ = self.cmd('cat {0}/{1}_rman.log'.format(location, db_name[:-1]))
                else:
                    logging.info('Unable to find {0}/{1}_rman.log, attempting using instance name'.format(location,
                                                                                                          db_name))
                    lines, __, __ = self.cmd('cat {0}/{1}_rman.log'.format(location, sid))
                    if not lines:
                        raise e

        # Remove empty lines
        lines = [line for line in lines if line]

        # If job specified, return only lines for that job
        if job:
            try:
                return self.get_jobs_in_lines(lines=lines)[job]
            except KeyError:
                raise RuntimeError('{0} not found in rman log'.format(job))
        else:
            return lines

    @staticmethod
    def get_jobs_in_lines(lines):
        base_dict = {}
        hook = '********Job_'
        sections = [line.replace('*', '') for line in lines if hook in line]
        indices = [i for i, line in enumerate(lines) if hook in line]
        for i, number in enumerate(indices):
            if i + 1 == len(indices):
                base_dict[sections[i]] = lines[number + 1:]
            else:
                base_dict[sections[i]] = lines[number + 1:indices[i + 1]]
        return base_dict

# Error classes


class OutputError(Exception):

    def __init__(self, errorcode, errormessage):
        self.errormessage = errormessage
        self.errorcode = errorcode
        self.msg = '{0}: {1}'.format(self.errorcode, self.errormessage)

    def __str__(self):
        return self.msg


class OracleError(OutputError):
    """
    Oracle exception object for (ORA-#####) type errors.
    Oracle errors are sent to stdout and must be caught.
    """


class SQLPlusError(OutputError):
    """
    SQLPlus exception object for (SP2-####) type errors.
    SQLPlus errors are sent to stdout and must be caught.
    """


class RMANError(OutputError):
    """
    RMAN exception object for 'RMAN-#####' errors
    """


class SQLServerError(OutputError):
    """
    SQLCmd and SQLServer exception object for 'Msg ###' 'Error message'
    """
