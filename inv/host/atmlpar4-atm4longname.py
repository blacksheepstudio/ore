from rf_inventory import get_host_variables

variables = {'name': 'atmlpar4', 'ip': '172.27.36.20', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'atm4longname', 'app_type': 'Oracle', 'apps': ['/', 'atm4longname'], 'app_list': ['/', 'atm4longname'], 'app_exclude': ['/'], 'cluster_ip': '172.27.36.20', 'racnodelist': '172.27.36.20', 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'atm4longname', 'oracle_home': '/u01/ordb/oracle/product/11.2.0', 'oracle_path': '/u01/ordb/oracle/product/11.2.0/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/u01/ordb/oracle/product/11.2.0', 'po_tnsadmindir': '/u01/ordb/oracle/product/11.2.0/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
