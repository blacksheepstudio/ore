# Oracle Regression Environment

## Guide for use:

Use ORE to:
- Manage environment containing multiple Oracle hosts with many databases
- Prepare RobotFramework test execution plans across hosts (in conjunction with RBC)
- Upgrade and monitor connectors on hosts in environment

## How to start running tests:

Before we are ready to run tests on our Oracle environment, we must make all the hosts/appliances/plans
known to ORE.
This is done by editing four yamls: **appliances.yml, databases.yml, plan.yml, executions.yml**

**Step 1)** 
    Make sure you have framework3 installed and you have built the latest docker image:
        [Framework3](https://git.build.actifio.com/testing_tools/framework3)

**Step 2)**
    Make sure your rbc_settings.yml variables are all set correctly.
    
**Step 3)** 
Edit appliances.yml with entries for each appliance, e.g:

```
orasky1:
inventory_file: "orasky1.py"
appliance_type: "sky"
ipaddress: "172.27.20.201"
```

**Step 4)**

Edit databases.yml and add in your hosts/databases, e.g:

```
atmlpar4:
    ipaddress: "172.27.36.20"
    platform: "AIX"
    databases:
    - atm4longname:
        inventory_file: "atmlpar4-atm4longname.py"
        oracle_sid: "atm4longname"
        oracle_home: "/u01/ordb/oracle/product/11.2.0"
        version: "11.2"
        testlink_platform: "AIX 6.1 Oracle 11g RAC ASM"
    - atmlpar4fs:
        inventory_file: "atmlpar4-atmlpar4fs.py"
        oracle_sid: "atmlpar4fs"
        oracle_home: "/u01/ordb/oracle/product/11.2.0"
        version: "11.2"
        testlink_platform: "AIX 6.1 Oracle 11g FS"
```

Once you have added all your databases and sky, create robot framework inventory for them:

*Issue this command from terminal:*
> python ore.py mkinv all

If you check in ./inv you should see a host and appliance directory, now filled with RobotFramework inventory.

**Step 5)**
Edit plan.yml and create your appliance/connector version matrix:
    
First you must create aliases for connector versions by listing exact directory on Garfield:

```
connectors:
    trunk: "https://garfield.build.actifio.com/files/builds/cdsky/trunk/8.0.0/8.0.0.1458/"
    sp713: "https://garfield.build.actifio.com/files/builds/cdsky/sp-7.1.3/7.1.3/7.1.3.273/"
    sp715: "https://garfield.build.actifio.com/files/builds/cdsky/sp-7.1.5/7.1.5/7.1.5.406/" 
```

Then you must create appliance/host/version relationships:

```
# Host name
ore-rhel11g-1:
    # Branch alias
    branch: trunk
    # Appliance name
    appliance: orasky3
ndm4-vm:
    branch: trunk
    appliance: orasky3
# Add more
```

**Step 6)**

Finally you must edit the executions.yml, this is the most important part:

**Terms**

- Layers: A layer is a set of tests that will all run IN PARALLEL
- Execution Profile: Combining a set of Layers, a robot suite, and any number of parameters for test run.
    
First let's create a set of layers.
A Layer is any number of hosts/databases that can run in parallel, without disrupting each other:

```
layers:
  layer1:
    nstlpar24:
      database: ora111db
    atmlpar4:
      database: atmlpar4fs
    atmlpar9:
      database: ix11R2db
  layer2:
    nstlpar24:
      database: nextdb
    atmlpar4:
      database: anotherdb
    atmlpar9:
      database: yetanother
  layer3:
    # etc ...
```
  
Once you have created your layers, (In the following example we have created 3 layers),
You must create execution profiles:
Here is an example of the Execution Profile tab:

```
executions:
    # This profile will run a standard suite, with no params, on three layers
    mounts_default:
        label: run mount suite with default options
        layers:
          - layer1
          - layer2
          - layer3
        suite: suites/ora2/logsmart_mounts1.robot
        variables:
    # This profile will run the same set of layers, but with db authentication
    mounts_dbauth:
        label: run mount suite with db authentication
        layers:
          - layer1
          - layer2
          - layer3
        suite: suites/ora2/logsmart_mounts1.robot
        variables: authentication=db
```

**Step 7)**

Generate your aliases file, and execute tests:

> python ore.py aliases

> cat aliases.sh

```
nohup python rbc.py hpvm1_hpracdb_mounts_nonlogsmart_osauth_layer1 &
nohup python rbc.py atmlpar9_ix11R2db_mounts_nonlogsmart_osauth_layer1 &
nohup python rbc.py bb6aix3_bb12rcdb_mounts_nonlogsmart_osauth_layer1 &
nohup python rbc.py hpvm1_orafsdb_mounts_nonlogsmart_osauth_layer2 &
nohup python rbc.py atmlpar9_ax12cdb_mounts_nonlogsmart_osauth_layer2 &
nohup python rbc.py atmlpar4_atm4longname_mounts_nonlogsmart_osauth_layer2 &
```

Copy and past all of the elements from 'layer1' into the terminal.
You are now running robot tests.

You must wait for layer1 to complete, before you can copy and paste all the executions of layer2.

*While tests are running, their output will be sent to ./logs/<alias_name>.txt*

*Once a test has completed it will go to ./logs/<today's date>/<alias_name>.txt|html|xml*

--------------
### More Info

If you have created all the configuration files correctly, with no errors,
you should now be able to do a lot of things with ore.

*Generate a CSV of the testplan:*
> python ore.py mkcsv

*Check databases running / connector versions on all hosts:*
> python ore.py lshosts

*Clear archivelogs on all hosts:*
> python ore.py cleanuplogs all

*For a list of all commands, simply run:*
> python ore.py


