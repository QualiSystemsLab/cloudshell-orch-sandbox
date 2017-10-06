import unittest
from mock import patch, Mock, call
from sandbox_scripts.environment.setupS.setup_VM import EnvironmentSetupVM
from sandbox_scripts.QualiEnvironmentUtils.QualiUtils import QualiError
from cloudshell.api.common_cloudshell_api import CloudShellAPIError
from cloudshell.api.cloudshell_api import ResourceInfoVmDetails
import json
import os


resContext = '''{"id":"5487c6ce-d0b3-43e9-8ee7-e27af8406905",
 "ownerUser":"bob",
 "ownerPass":"nIqm+BG6ZGJjby5hUittVFFJASc=",
 "domain":"Global",
 "environmentName":"My environment",
 "description":"New demo environment",
 "parameters":
   { "globalInputs": [],
     "resourceRequirements":[],
     "resourceAdditionalInfo":[]}}'''

conContext = '''{"serverAddress": "localhost",
"adminAuthToken": "anAdminToken"}'''


class SetupVMTests(unittest.TestCase):

    @patch('sandbox_scripts.environment.setupS.setup_VM.get_qs_logger')
    def setUp(self, mock_logger):
        os.environ['reservationContext'] = resContext
        os.environ['qualiConnectivityContext'] = conContext
        self.setup_script = EnvironmentSetupVM()

    def tearDown(self):
        pass

    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    @patch('sandbox_scripts.environment.setupS.setup_VM.SandboxBase')
    @patch('sandbox_scripts.environment.setupS.setup_VM.SaveRestoreManager')
    def test_setup_vm_with_no_resources(self, mock_save, mock_sandboxbase, mock_api_session):

        self.setup_script.execute()

        report_info_calls = [call('Beginning VMs power on'),
                             call(message='No VMs to power on ', write_to_output_window=True)]
        mock_sandboxbase.return_value.report_info.assert_has_calls(report_info_calls)

    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    @patch('sandbox_scripts.environment.setupS.setup_VM.SandboxBase')
    @patch('sandbox_scripts.environment.setupS.setup_VM.SaveRestoreManager')
    def test_setup_vm_with_regular_resource(self, mock_save, mock_sandboxbase, mock_api_session):

        rdi = Mock()
        resource1 = Mock()
        resource1.Name = "r1"
        resource2 = Mock()
        resource2.Name = "r2"
        rdi.ReservationDescription.Resources = [resource1, resource2]
        rdi.ReservationDescription.TopologiesReservedResources = []
        rdi.ReservationDescription.Apps = []

        mock_sandboxbase.return_value.get_details.return_value = rdi

        def resource_details_mock_side_effect(name):
            rd = Mock()
            rd.details.Name = name
            rd.details.Address = ''
            if name == 'r1':
                rd.VmDetails = None
            elif name == 'r2':
                rd.VmDetails = object()
            return rd

        mock_sandboxbase.return_value.api_session.GetResourceDetails.side_effect = resource_details_mock_side_effect

        mock_save.return_value.is_snapshot.return_value = True

        self.setup_script.execute()

        report_info_calls = [call('Beginning VMs power on'),call(message='No VMs to power on ', write_to_output_window=True)]
        mock_sandboxbase.return_value.report_info.assert_has_calls(report_info_calls)


    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    @patch('sandbox_scripts.environment.setupS.setup_VM.SandboxBase')
    @patch('sandbox_scripts.environment.setupS.setup_VM.SaveRestoreManager')
    def test_setup_vm_with_static_app_resource_power_on_no_wait_for_ip(self, mock_save, mock_sandboxbase, mock_api_session):
        rdi = Mock()
        resource1 = Mock()
        resource1.Name = "r2"
        resource1.ResourceModelName = 'vcenter static vm'
        rdi.ReservationDescription.Resources = [resource1]
        rdi.ReservationDescription.TopologiesReservedResources = []
        rdi.ReservationDescription.Apps = []

        mock_sandboxbase.return_value.get_details.return_value = rdi

        def resource_details_mock_side_effect(name):
            rd = Mock()
            rd.details.Name = name
            rd.details.Address = ''
            rd.VmDetails = Mock()
            rd.VmDetails.UID = 'abcd'
            return rd

        mock_sandboxbase.return_value.api_session.GetResourceDetails.side_effect = resource_details_mock_side_effect

        resourcebase1 = Mock()
        resourcebase1.name = 'r2'
        resourcebase1.model = 'vcenter static vm'
        mock_sandboxbase.return_value.get_root_vm_resources.return_value = [resourcebase1]

        mock_save.return_value.is_snapshot.return_value = False

        self.setup_script.execute()

        report_info_calls = [call('Beginning VMs power on'),
                             call('Apps are powering on... '),
                             call(log_message="Executing 'Power On' on deployed app 'r2' in reservation "
                                              "'5487c6ce-d0b3-43e9-8ee7-e27af8406905'",
                                  message="Executing 'Power On' on deployed app 'r2' ", write_to_output_window=True),
                             call("Wait For IP is off for deployed app 'r2' in reservation "
                                  "'5487c6ce-d0b3-43e9-8ee7-e27af8406905'")]
        mock_sandboxbase.return_value.report_info.assert_has_calls(report_info_calls)

        logger_debug_calls = [call("Resource r2 is a static app")]
        self.setup_script.logger.debug.assert_has_calls(logger_debug_calls)

        api_calls = [call.execute_connected_command(u'5487c6ce-d0b3-43e9-8ee7-e27af8406905', 'PowerOn', 'power')]
        resourcebase1.assert_has_calls(api_calls)


    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    @patch('sandbox_scripts.environment.setupS.setup_VM.SandboxBase')
    @patch('sandbox_scripts.environment.setupS.setup_VM.SaveRestoreManager')
    def test_setup_vm_with_deployed_app_resource(self, mock_save, mock_sandboxbase, mock_api_session):
        rdi = Mock()
        resource1 = Mock()
        resource1.Name = "r2"
        resource1.ResourceModelName = 'deployed app'
        rdi.ReservationDescription.Resources = [resource1]
        rdi.ReservationDescription.TopologiesReservedResources = []
        rdi.ReservationDescription.Apps = []

        mock_sandboxbase.return_value.get_details.return_value = rdi

        def resource_details_mock_side_effect(name):
            rd = Mock()
            rd.details.Name = name
            rd.details.Address = ''
            rd.VmDetails = Mock()
            rd.VmDetails.UID = 'abcd'
            return rd

        mock_sandboxbase.return_value.api_session.GetResourceDetails.side_effect = resource_details_mock_side_effect

        resourcebase1 = Mock()
        resourcebase1.name = 'r2'
        resourcebase1.model = 'deployed app'
        mock_sandboxbase.return_value.get_root_vm_resources.return_value = [resourcebase1]

        mock_save.return_value.is_snapshot.return_value = True

        self.setup_script.execute()

        report_info_calls = [call('Beginning VMs power on'),
                             call('Apps are powering on... '),
                             call(log_message="Executing 'Power On' on deployed app 'r2' in reservation "
                                              "'5487c6ce-d0b3-43e9-8ee7-e27af8406905'",
                                  message="Executing 'Power On' on deployed app 'r2' ", write_to_output_window=True),
                             call(message='Waiting for apps IP addresses, this may take a while...',
                                  write_to_output_window=True)]
        mock_sandboxbase.return_value.report_info.assert_has_calls(report_info_calls)

        api_calls = [call.execute_connected_command(u'5487c6ce-d0b3-43e9-8ee7-e27af8406905', 'PowerOn', 'power'),
                    call.execute_connected_command(u'5487c6ce-d0b3-43e9-8ee7-e27af8406905', 'remote_refresh_ip', 'remote_connectivity')]
        resourcebase1.assert_has_calls(api_calls)

if __name__ == '__main__':
    unittest.main()
