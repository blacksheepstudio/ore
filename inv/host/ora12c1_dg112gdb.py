from rf_inventory import get_host_variables

variables = {'name': 'ora12c1', 'ip': '172.17.200.213', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'dg112gdb', 'app_type': 'Oracle', 'apps': ['/', 'dg112gdb'], 'app_list': ['/', 'dg112gdb'], 'app_exclude': ['/'], 'cluster_ip': '172.17.200.213', 'racnodelist': '172.17.200.213', 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'dg112gdb1', 'oracle_home': '/oracle/app/11.2.0/dbhome_1', 'oracle_path': '/oracle/app/11.2.0/dbhome_1/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/oracle/app/11.2.0/dbhome_1', 'po_tnsadmindir': '/oracle/app/11.2.0/dbhome_1/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
