from rf_inventory import get_host_variables

variables = {'name': 'ore-rhel11g-1', 'ip': '172.27.20.246', 'ssh_user': 'root', 'ssh_pass': '12!pass345', 'ssh_private_key_file': '', 'app': 'oriondb', 'app_type': 'Oracle', 'apps': ['/', 'oriondb'], 'app_list': ['/', 'oriondb'], 'app_exclude': ['/'], 'cluster_ip': None, 'racnodelist': None, 'oracle_user': 'oracle', 'oracle_pass': '12!pass345', 'oracle_sid': 'oriondb', 'oracle_home': '/u01/app/oracle/product/11.2.0.3/db_1', 'oracle_path': '/u01/app/oracle/product/11.2.0.3/db_1/bin', 'po_databasesid': 'achild', 'po_username': 'oracle', 'po_orahome': '/u01/app/oracle/product/11.2.0.3/db_1', 'po_tnsadmindir': '/u01/app/oracle/product/11.2.0.3/db_1/network/admin', 'po_totalmemory': '800', 'po_sgapct': '70'}


def get_variables(prepend=None, append=None, delimiter='.', base=variables):
    return get_host_variables(base=base, prepend=prepend, append=append, delimiter=delimiter)
