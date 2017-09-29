from rf_inventory import get_host_variables

variables = {'name': 'ndm4-vm', 'ip': '172.27.11.211', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'ort205db', 'app_type': 'Oracle', 'apps': ['/', 'ort205db'], 'app_list': ['/', 'ort205db'], 'app_exclude': ['/'], 'cluster_ip': '172.27.11.211', 'racnodelist': '172.27.11.211', 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'ort205db1', 'oracle_home': '/u01/app/oracle/product/10.2.0/db_1', 'oracle_path': '/u01/app/oracle/product/10.2.0/db_1/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/u01/app/oracle/product/10.2.0/db_1', 'po_tnsadmindir': '/u01/app/oracle/product/10.2.0/db_1/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
