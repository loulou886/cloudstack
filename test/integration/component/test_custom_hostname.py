# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
""" P1 tests for user provide hostname cases
"""
#Import Local Modules
import marvin
from nose.plugins.attrib import attr
from marvin.cloudstackTestCase import *
from marvin.integration.lib.utils import *
from marvin.integration.lib.base import *
from marvin.integration.lib.common import *


class Services:
    """Test user provided hostname Services
    """

    def __init__(self):
        self.services = {
                        "domain": {
                                   "name": "Domain",
                        },
                        "project": {
                                    "name": "Project",
                                    "displaytext": "Test project",
                        },
                        "account": {
                                    "email": "administrator@clogeny.com",
                                    "firstname": "Test",
                                    "lastname": "User",
                                    "username": "test",
                                    # Random characters are appended for unique
                                    # username
                                    "password": "password",
                         },
                         "user": {
                                    "email": "administrator@clogeny.com",
                                    "firstname": "User",
                                    "lastname": "User",
                                    "username": "User",
                                    # Random characters are appended for unique
                                    # username
                                    "password": "password",
                         },
                        "disk_offering": {
                                    "displaytext": "Tiny Disk Offering",
                                    "name": "Tiny Disk Offering",
                                    "disksize": 1
                        },
                        "volume": {
                                "diskname": "Test Volume",
                        },
                        "service_offering": {
                                    "name": "Tiny Instance",
                                    "displaytext": "Tiny Instance",
                                    "cpunumber": 1,
                                    "cpuspeed": 100, # in MHz
                                    "memory": 128, # In MBs
                        },
                        "virtual_machine": {
                                    "displayname": "TestVM",
                                    "username": "root",
                                    "password": "password",
                                    "ssh_port": 22,
                                    "hypervisor": 'XenServer',
                                    # Hypervisor type should be same as
                                    # hypervisor type of cluster
                                    "privateport": 22,
                                    "publicport": 22,
                                    "protocol": 'TCP',
                         },
                        "ostype": 'CentOS 5.3 (64-bit)',
                        # Cent OS 5.3 (64 bit)
                        "sleep": 60,
                        "timeout": 10,
                    }


class TestInstanceNameFlagTrue(cloudstackTestCase):

    @classmethod
    def setUpClass(cls):
        cls.api_client = super(
                               TestInstanceNameFlagTrue,
                               cls
                               ).getClsTestClient().getApiClient()
        cls.services = Services().services
        # Get Zone, default template
        cls.zone = get_zone(cls.api_client, cls.services)
        cls.services["mode"] = cls.zone.networktype
        cls.template = get_template(
                            cls.api_client,
                            cls.zone.id,
                            cls.services["ostype"]
                            )

        # Create domains, account etc.
        cls.domain = get_domain(
                                   cls.api_client,
                                   cls.services
                                   )

        cls.account = Account.create(
                            cls.api_client,
                            cls.services["account"],
                            admin=True,
                            domainid=cls.domain.id
                            )

        cls.services["virtual_machine"]["zoneid"] = cls.zone.id
        cls.services["virtual_machine"]["template"] = cls.template.id

        cls.service_offering = ServiceOffering.create(
                                            cls.api_client,
                                            cls.services["service_offering"]
                                            )
        cls._cleanup = [cls.account]
        return

    @classmethod
    def tearDownClass(cls):
        try:
            #Cleanup resources used
            cleanup_resources(cls.api_client, cls._cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    def setUp(self):
        self.apiclient = self.testClient.getApiClient()
        self.dbclient = self.testClient.getDbConnection()
        self.cleanup = []
        return

    def tearDown(self):
        try:
            #Clean up, terminate the created accounts, domains etc
            cleanup_resources(self.apiclient, self.cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return



    @attr(configuration='vm.instancename.flag')
    @attr(tags=["advanced", "basic", "sg", "eip", "advancedns", "simulator"])
    def test_01_user_provided_hostname(self):
        """ Verify user provided hostname to an instance
        """

        # Validate the following
        # 1. Set the vm.instancename.flag to true. Hostname and displayname
        #    should be user provided display name
        # 2. Give the user provided user name. Internal name should be
        #    i-<userid>-<vmid>-display name
        if not is_config_suitable(apiclient=self.apiclient, name='vm.instancename.flag', value='true'):
            self.skipTest('vm.instancename.flag should be true. skipping')

        self.debug("Deploying VM in account: %s" % self.account.name)
        # Spawn an instance in that network
        virtual_machine = VirtualMachine.create(
                                  self.apiclient,
                                  self.services["virtual_machine"],
                                  accountid=self.account.name,
                                  domainid=self.account.domainid,
                                  serviceofferingid=self.service_offering.id,
                                  )
        self.debug(
            "Checking if the virtual machine is created properly or not?")
        vms = VirtualMachine.list(
                                  self.apiclient,
                                  id=virtual_machine.id,
                                  listall=True
                                  )

        self.assertEqual(
                         isinstance(vms, list),
                         True,
                         "List vms should return a valid name"
                         )
        vm = vms[0]
        self.assertEqual(
                         vm.state,
                         "Running",
                         "Vm state should be running after deployment"
                         )
        self.debug("vm.displayname: %s, original: %s" %
                        (vm.displayname,
                        self.services["virtual_machine"]["displayname"]))
        self.assertEqual(
                         vm.displayname,
                         self.services["virtual_machine"]["displayname"],
                         "Vm display name should match the given name"
                         )

        # Fetch account ID and VMID from database to check internal name
        self.debug("select id from account where uuid = '%s';" \
                                            % self.account.id)

        qresultset = self.dbclient.execute(
                                "select id from account where uuid = '%s';" \
                                % self.account.id
                                )
        self.assertEqual(
                         isinstance(qresultset, list),
                         True,
                         "Check DB query result set for valid data"
                         )

        self.assertNotEqual(
                            len(qresultset),
                            0,
                            "Check DB Query result set"
                            )
        qresult = qresultset[0]
        account_id = qresult[0]

        self.debug("select id from vm_instance where uuid = '%s';" % vm.id)

        qresultset = self.dbclient.execute(
                        "select id from vm_instance where uuid = '%s';" %
                        vm.id)

        self.assertEqual(
                         isinstance(qresultset, list),
                         True,
                         "Check DB query result set for valid data"
                         )

        self.assertNotEqual(
                            len(qresultset),
                            0,
                            "Check DB Query result set"
                            )
        qresult = qresultset[0]
        self.debug("Query result: %s" % qresult)
        vmid = qresult[0]

        #internal Name = i-<user ID>-<VM ID>-Display name
        internal_name = "i-" + str(account_id) + "-" + str(vmid) + "-" + vm.displayname
        self.debug("Internal name: %s" % internal_name)
        self.assertEqual(
                        vm.instancename,
                        internal_name,
                        "VM internal name should match with that of the format"
                        )
        return

    @attr(configuration='vm.instancename.flag')
    @attr(tags=["advanced", "basic", "sg", "eip", "advancedns", "simulator"])
    def test_02_instancename_from_default_configuration(self):
        """ Verify for globally set instancename
        """

        # Validate the following
        # 1. Set the vm.instancename.flag to true. Hostname and displayname
        #    should be user provided display name
        # 2. Dont give the user provided user name. Internal name should be
        #    i-<userid>-<vmid>-<instance.name> in global config
        if not is_config_suitable(apiclient=self.apiclient, name='vm.instancename.flag', value='true'):
            self.skipTest('vm.instancename.flag should be true. skipping')

        # Removing display name from config
        del self.services["virtual_machine"]["displayname"]
        self.debug("Deploying VM in account: %s" % self.account.name)
        virtual_machine = VirtualMachine.create(
                                  self.apiclient,
                                  self.services["virtual_machine"],
                                  accountid=self.account.name,
                                  domainid=self.account.domainid,
                                  serviceofferingid=self.service_offering.id,
                                  )
        self.debug(
            "Checking if the virtual machine is created properly or not?")
        vms = VirtualMachine.list(
                                  self.apiclient,
                                  id=virtual_machine.id,
                                  listall=True
                                  )

        self.assertEqual(
                         isinstance(vms, list),
                         True,
                         "List vms should retuen a valid name"
                         )
        vm = vms[0]
        self.assertEqual(
                         vm.state,
                         "Running",
                         "Vm state should be running after deployment"
                         )
        self.assertNotEqual(
                         vm.displayname,
                         vm.id,
                         "Vm display name should not match the given name"
                         )
        # Fetch account ID and VMID from database to check internal name
        self.debug("select id from account where uuid = '%s';" \
                                            % self.account.id)

        qresultset = self.dbclient.execute(
                                "select id from account where uuid = '%s';" \
                                % self.account.id
                                )
        self.assertEqual(
                         isinstance(qresultset, list),
                         True,
                         "Check DB query result set for valid data"
                         )

        self.assertNotEqual(
                            len(qresultset),
                            0,
                            "Check DB Query result set"
                            )
        qresult = qresultset[0]
        account_id = qresult[0]

        self.debug("select id from vm_instance where uuid = '%s';" % vm.id)

        qresultset = self.dbclient.execute(
                        "select id from vm_instance where uuid = '%s';" %
                        vm.id)

        self.assertEqual(
                         isinstance(qresultset, list),
                         True,
                         "Check DB query result set for valid data"
                         )

        self.assertNotEqual(
                            len(qresultset),
                            0,
                            "Check DB Query result set"
                            )
        qresult = qresultset[0]
        self.debug("Query result: %s" % qresult)
        vmid = qresult[0]

        self.debug("Fetching the global config value for instance.name")
        configs = Configurations.list(
                                      self.apiclient,
                                      name="instance.name",
                                      listall=True
                                      )

        config = configs[0]
        instance_name = config.value
        self.debug("Instance.name: %s" % instance_name)

        #internal Name = i-<user ID>-<VM ID>- Instance_name
        internal_name = "i-" + str(account_id) + "-" + str(vmid) + "-" + instance_name
        self.assertEqual(
                        vm.instancename,
                        internal_name,
                        "VM internal name should match with that of the format"
                        )
        return

    @attr(configuration='vm.instancename.flag')
    @attr(tags=["advanced", "basic", "sg", "eip", "advancedns", "simulator"])
    def test_03_duplicate_name(self):
        """ Test the duplicate name when old VM is in non-expunged state
        """

        # Validate the following
        # 1. Set the vm.instancename.flag to true.
        # 2. Add the virtual machine with display name same as that of
        #   non-expunged virtual machine. The proper error should pop
        #   out saying the duplicate names are not allowed

        # Reading display name property
        if not is_config_suitable(apiclient=self.apiclient, name='vm.instancename.flag', value='true'):
            self.skipTest('vm.instancename.flag should be true. skipping')

        self.services["virtual_machine"]["displayname"] = "TestVM"
        self.services["virtual_machine"]["name"] = "TestVM"

        self.debug("Deploying an instance in account: %s" %
                                        self.account.name)

        virtual_machine = VirtualMachine.create(
                                  self.apiclient,
                                  self.services["virtual_machine"],
                                  accountid=self.account.name,
                                  domainid=self.account.domainid,
                                  serviceofferingid=self.service_offering.id,
                                  )
        self.debug(
            "Checking if the virtual machine is created properly or not?")
        vms = VirtualMachine.list(
                                  self.apiclient,
                                  id=virtual_machine.id,
                                  listall=True
                                  )

        self.assertEqual(
                         isinstance(vms, list),
                         True,
                         "List vms should retuen a valid name"
                         )
        vm = vms[0]
        self.assertEqual(
                         vm.state,
                         "Running",
                         "Vm state should be running after deployment"
                         )
        self.debug("Display name: %s" % vm.displayname)
        self.debug("Deplying another virtual machine with same name")
        with self.assertRaises(Exception):
            VirtualMachine.create(
                                  self.apiclient,
                                  self.services["virtual_machine"],
                                  accountid=self.account.name,
                                  domainid=self.account.domainid,
                                  serviceofferingid=self.service_offering.id,
                                  )
        return

    @attr(configuration='vm.instancename.flag')
    @attr(tags=["advanced", "basic", "sg", "eip", "advancedns", "simulator"])
    def test_04_edit_display_name(self):
        """ Test Edit the Display name Through the UI.
        """

        # Validate the following
        # 1) Set the Global Setting vm.instancename.flag to true
        # 2) Create a VM give a Display name.
        # 3) Once the VM is created stop the VM.
        # 4) Edit the VM Display name. The Display name will be changed but the
        #    internal name will not be changed. The VM functionality must not
        #    be effected.

        self.services["virtual_machine"]["name"] = "TestVM4"
        # Spawn an instance in that network
        self.debug("Deploying VM in account: %s" % self.account.name)
        virtual_machine = VirtualMachine.create(
                                  self.apiclient,
                                  self.services["virtual_machine"],
                                  accountid=self.account.name,
                                  domainid=self.account.domainid,
                                  serviceofferingid=self.service_offering.id,
                                  )
        self.debug(
            "Checking if the virtual machine is created properly or not?")
        vms = VirtualMachine.list(
                                  self.apiclient,
                                  id=virtual_machine.id,
                                  listall=True
                                  )

        self.assertEqual(
                         isinstance(vms, list),
                         True,
                         "List vms should retuen a valid name"
                         )
        vm = vms[0]
        self.assertEqual(
                         vm.state,
                         "Running",
                         "Vm state should be running after deployment"
                         )

        self.assertEqual(
                         vm.displayname,
                         self.services["virtual_machine"]["displayname"],
                         "Vm display name should match the given name"
                         )

        old_internal_name = vm.instancename
        self.debug("Stopping the instance: %s" % vm.name)
        try:
            virtual_machine.stop(self.apiclient)
        except Exception as e:
            self.fail("Failed to stop instance: %s, %s" % (vm.name, e))

        self.debug("Update the display name of the instance")
        try:
            virtual_machine.update(self.apiclient, displayname=random_gen())
        except Exception as e:
            self.fail("Failed to update the virtual machine name: %s, %s" %
                                                (virtual_machine.name, e))

        self.debug("Start the instance: %s" % virtual_machine.name)
        virtual_machine.start(self.apiclient)

        self.debug("Checking if the instance is working properly after update")
        vms = VirtualMachine.list(
                                  self.apiclient,
                                  id=virtual_machine.id,
                                  listall=True
                                  )

        self.assertEqual(
                         isinstance(vms, list),
                         True,
                         "List vms should retuen a valid name"
                         )
        vm = vms[0]
        self.assertEqual(
                         vm.state,
                         "Running",
                         "Vm state should be running after deployment"
                         )

        self.assertEqual(
                         vm.instancename,
                         old_internal_name,
                         "Vm internal name should not be changed after update"
                         )
        return

    @attr(configuration='vm.instancename.flag')
    @attr(tags=["advanced", "basic", "sg", "eip", "advancedns", "simulator"])
    def test_05_unsupported_chars_in_display_name(self):
        """ Test Unsupported chars in the display name
            (eg: Spaces,Exclamation,yet to get unsupported chars from the dev)
        """

        # Validate the following
        # 1) Set the Global Setting vm.instancename.flag to true
        # 2) While creating VM give a Display name which has unsupported chars
        #    Gives an error message "Instance name can not be longer than 63
        #    characters. Only ASCII letters a~z, A~Z, digits 0~9, hyphen are
        #    allowed. Must start with a letter and end with a letter or digit

        self.debug("Creating VM with unsupported chars in display name")
        display_names = ["!hkzs566", "asdh asd", "!dsf d"]

        for display_name in display_names:
            self.debug("Display name: %s" % display_name)
            self.services["virtual_machine"]["displayname"] = display_name

            with self.assertRaises(Exception):
                # Spawn an instance in that network
                VirtualMachine.create(
                                  self.apiclient,
                                  self.services["virtual_machine"],
                                  accountid=self.account.name,
                                  domainid=self.account.domainid,
                                  serviceofferingid=self.service_offering.id,
                                  )
        return


class TestInstanceNameFlagFalse(cloudstackTestCase):

    @classmethod
    def setUpClass(cls):
        cls.api_client = super(
                               TestInstanceNameFlagFalse,
                               cls
                               ).getClsTestClient().getApiClient()
        cls.services = Services().services
        # Get Zone, default template
        cls.zone = get_zone(cls.api_client, cls.services)

        cls.template = get_template(
                            cls.api_client,
                            cls.zone.id,
                            cls.services["ostype"]
                            )

        # Create domains, account etc.
        cls.domain = get_domain(
                                   cls.api_client,
                                   cls.services
                                   )

        cls.account = Account.create(
                            cls.api_client,
                            cls.services["account"],
                            admin=True,
                            domainid=cls.domain.id
                            )

        cls.services["virtual_machine"]["zoneid"] = cls.zone.id
        cls.services["virtual_machine"]["template"] = cls.template.id

        cls.service_offering = ServiceOffering.create(
                                            cls.api_client,
                                            cls.services["service_offering"]
                                            )
        cls._cleanup = [cls.account]
        return

    @classmethod
    def tearDownClass(cls):
        try:
            #Cleanup resources used
            cleanup_resources(cls.api_client, cls._cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    def setUp(self):
        self.apiclient = self.testClient.getApiClient()
        self.dbclient = self.testClient.getDbConnection()
        self.cleanup = []
        return

    def tearDown(self):
        try:
            #Clean up, terminate the created accounts, domains etc
            cleanup_resources(self.apiclient, self.cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    @attr(configuration='vm.instancename.flag')
    @attr(tags=["advanced", "basic", "sg", "eip", "advancedns", "simulator"])
    def test_01_custom_hostname_instancename_false(self):
        """ Verify custom hostname for the instance when
            vm.instancename.flag=false
        """

        # Validate the following
        # 1. Set the vm.instancename.flog to false. Hostname and displayname
        #    should be UUID
        # 2. Give the user provided user name. Internal name should be
        #    i-<userid>-<vmid>-display name

        if not is_config_suitable(apiclient=self.apiclient, name='vm.instancename.flag', value='false'):
            self.skipTest('vm.instancename.flag should be false. skipping')

        self.debug("Deploying VM in account: %s" % self.account.name)
        # Spawn an instance in that network
        virtual_machine = VirtualMachine.create(
                                  self.apiclient,
                                  self.services["virtual_machine"],
                                  accountid=self.account.name,
                                  domainid=self.account.domainid,
                                  serviceofferingid=self.service_offering.id,
                                  )
        self.debug(
            "Checking if the virtual machine is created properly or not?")
        vms = VirtualMachine.list(
                                  self.apiclient,
                                  id=virtual_machine.id,
                                  listall=True
                                  )

        self.assertEqual(
                         isinstance(vms, list),
                         True,
                         "List vms should retuen a valid name"
                         )
        vm = vms[0]
        self.assertEqual(
                         vm.state,
                         "Running",
                         "Vm state should be running after deployment"
                         )
        self.debug("VM diaplyname: %s" % (vm))
        self.assertEqual(
                         vm.name,
                         vm.id,
                         "Vm display name should match the given name"
                         )

        # Fetch account ID and VMID from database to check internal name
        self.debug("select id from account where uuid = '%s';" \
                                            % self.account.id)

        qresultset = self.dbclient.execute(
                                "select id from account where uuid = '%s';" \
                                % self.account.id
                                )
        self.assertEqual(
                         isinstance(qresultset, list),
                         True,
                         "Check DB query result set for valid data"
                         )

        self.assertNotEqual(
                            len(qresultset),
                            0,
                            "Check DB Query result set"
                            )
        qresult = qresultset[0]
        account_id = qresult[0]

        self.debug("select id from vm_instance where uuid = '%s';" % vm.id)

        qresultset = self.dbclient.execute(
                        "select id from vm_instance where uuid = '%s';" %
                        vm.id)

        self.assertEqual(
                         isinstance(qresultset, list),
                         True,
                         "Check DB query result set for valid data"
                         )

        self.assertNotEqual(
                            len(qresultset),
                            0,
                            "Check DB Query result set"
                            )
        qresult = qresultset[0]
        self.debug("Query result: %s" % qresult)
        vmid = qresult[0]

        self.debug("Fetching the global config value for instance.name")
        configs = Configurations.list(
                                      self.apiclient,
                                      name="instance.name",
                                      listall=True
                                      )

        config = configs[0]
        self.debug("Config value : %s"  % config)
        instance_name = config.value
        self.debug("Instance.name: %s" % instance_name)

        #internal Name = i-<user ID>-<VM ID>-<instance_name>
        #internal_name = "i-" + str(account_id) + "-" + str(vmid) + "-" + instance_name
        internal_name = "i-%s-%s-%s" %(str(account_id), str(vmid), instance_name)
        self.debug("Internal name: %s" % internal_name)
        self.debug("vm instance name : %s" % vm.instancename)
        self.assertEqual(
                        vm.instancename,
                        internal_name,
                        "VM internal name should match with that of the format"
                        )
        return

    @attr(configuration='vm.instancename.flag')
    @attr(tags=["advanced", "basic", "sg", "eip", "advancedns", "simulator"])
    def test_02_custom_hostname_instancename_false(self):
        """ Verify custom hostname for the instance when
            vm.instancename.flag=false
        """

        # Validate the following
        # 1. Set the vm.instancename.flag to false. Hostname and displayname
        #    should be UUID
        # 2. Dont give the user provided user name. Internal name should be
        #    i-<userid>-<vmid>-instance name

        if not is_config_suitable(apiclient=self.apiclient, name='vm.instancename.flag', value='false'):
            self.skipTest('vm.instancename.flag should be false. skipping')

        self.debug("Deploying VM in account: %s" % self.account.name)
        # Spawn an instance in that network
        virtual_machine = VirtualMachine.create(
                                  self.apiclient,
                                  self.services["virtual_machine"],
                                  accountid=self.account.name,
                                  domainid=self.account.domainid,
                                  serviceofferingid=self.service_offering.id,
                                  )
        self.debug(
            "Checking if the virtual machine is created properly or not?")
        vms = VirtualMachine.list(
                                  self.apiclient,
                                  id=virtual_machine.id,
                                  listall=True
                                  )

        self.assertEqual(
                         isinstance(vms, list),
                         True,
                         "List vms should retuen a valid name"
                         )
        vm = vms[0]
        self.assertEqual(
                         vm.state,
                         "Running",
                         "Vm state should be running after deployment"
                         )
        self.assertEqual(
                         vm.name,
                         vm.id,
                         "Vm display name should not match the given name"
                         )

        # Fetch account ID and VMID from database to check internal name
        self.debug("select id from account where uuid = '%s';" \
                                            % self.account.id)

        qresultset = self.dbclient.execute(
                                "select id from account where uuid = '%s';" \
                                % self.account.id
                                )
        self.assertEqual(
                         isinstance(qresultset, list),
                         True,
                         "Check DB query result set for valid data"
                         )

        self.assertNotEqual(
                            len(qresultset),
                            0,
                            "Check DB Query result set"
                            )
        qresult = qresultset[0]
        account_id = qresult[0]

        self.debug("select id from vm_instance where uuid = '%s';" % vm.id)

        qresultset = self.dbclient.execute(
                        "select id from vm_instance where uuid = '%s';" %
                        vm.id)

        self.assertEqual(
                         isinstance(qresultset, list),
                         True,
                         "Check DB query result set for valid data"
                         )

        self.assertNotEqual(
                            len(qresultset),
                            0,
                            "Check DB Query result set"
                            )
        qresult = qresultset[0]
        self.debug("Query result: %s" % qresult)
        vmid = qresult[0]

        self.debug("Fetching the global config value for instance.name")
        configs = Configurations.list(
                                      self.apiclient,
                                      name="instance.name",
                                      listall=True
                                      )

        config = configs[0]
        instance_name = config.value
        self.debug("Instance.name: %s" % instance_name)

        #internal Name = i-<user ID>-<VM ID>- Instance_name
        #internal_name = "i-" + str(account_id) + "-" + str(vmid) + "-" + instance_name
        internal_name = "i-%s-%s-%s" %(str(account_id), str(vmid), instance_name)
        self.debug("Internal_name : %s" % internal_name )
        self.assertEqual(
                        vm.instancename,
                        internal_name,
                        "VM internal name should match with that of the format"
                        )
        return