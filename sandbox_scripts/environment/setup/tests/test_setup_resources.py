import unittest
from mock import patch, Mock, call
from sandbox_scripts.environment.setup.setup_resources import EnvironmentSetupResources
from sandbox_scripts.QualiEnvironmentUtils.QualiUtils import QualiError
from cloudshell.api.common_cloudshell_api import CloudShellAPIError
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

class SetupResourcesTests(unittest.TestCase):

    @patch('sandbox_scripts.environment.setup.setup_resources.get_qs_logger')
    def setUp(self, mock_logger):
        os.environ['reservationContext'] = resContext
        os.environ['qualiConnectivityContext'] = conContext
        self.setup_script = EnvironmentSetupResources()

    def tearDown(self):
        pass

    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    @patch('sandbox_scripts.environment.setup.setup_resources.SandboxBase')
    @patch('sandbox_scripts.environment.setup.setup_resources.SaveRestoreManager')
    def test_flow_ok_with_snapshots(self, mock_save, mock_sandboxbase, mock_api_session):

        mock_save.return_value.is_snapshot.return_value = True
        self.setup_script.execute()
        mock_sandboxbase.return_value.clear_all_resources_live_status.assert_called_with(['Generic TFTP server', 'Config Set Pool', 'Generic FTP server', 'netscout switch 3912', 'Subnet-28', 'Subnet-30', 'GitLab', 'SSID_Pool'])
        mock_save.return_value.load_config.assert_called_with(config_stage='Snapshots', config_type='Running', ignore_models=['Generic TFTP server', 'Config Set Pool', 'Generic FTP server', 'netscout switch 3912', 'Subnet-28', 'Subnet-30', 'GitLab', 'SSID_Pool'])
        mock_sandboxbase.return_value.power_on_vms.assert_called_with()
        mock_sandboxbase.return_value.activate_all_routes_and_connectors.assert_called_with()
        report_info_calls = [call('Beginning load configuration for resources'),
                             call('Clearing status indicators ', write_to_output_window=True),
                             call('Sandbox setup finished.', write_to_output_window=True)]
        mock_sandboxbase.return_value.report_info.assert_has_calls(report_info_calls)


    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    @patch('sandbox_scripts.environment.setup.setup_resources.SandboxBase')
    @patch('sandbox_scripts.environment.setup.setup_resources.SaveRestoreManager')
    def test_flow_ok_with_gold(self, mock_save, mock_sandboxbase, mock_api_session):
        mock_save.return_value.is_snapshot.return_value = False
        mock_sandboxbase.return_value.get_storage_server_resource.return_value = True
        self.setup_script.execute()
        mock_sandboxbase.return_value.clear_all_resources_live_status.assert_called_with(
            ['Generic TFTP server', 'Config Set Pool', 'Generic FTP server', 'netscout switch 3912', 'Subnet-28',
             'Subnet-30', 'GitLab', 'SSID_Pool'])
        mock_save.return_value.load_config.assert_called_with(config_set_name='', config_stage='Gold', config_type='Running', ignore_models=['Generic TFTP server', 'Config Set Pool', 'Generic FTP server', 'netscout switch 3912', 'Subnet-28', 'Subnet-30', 'GitLab', 'SSID_Pool'])
        mock_sandboxbase.return_value.power_on_vms.assert_called_with()
        mock_sandboxbase.return_value.activate_all_routes_and_connectors.assert_called_with()
        report_info_calls = [call('Beginning load configuration for resources'),
                             call('Clearing status indicators ', write_to_output_window=True),
                             call('Sandbox setup finished.', write_to_output_window=True)]
        mock_sandboxbase.return_value.report_info.assert_has_calls(report_info_calls)

    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    @patch('sandbox_scripts.environment.setup.setup_resources.SandboxBase')
    @patch('sandbox_scripts.environment.setup.setup_resources.SaveRestoreManager')
    def test_flow_ok_with_no_storage_device(self, mock_save, mock_sandboxbase, mock_api_session):
        mock_sandboxbase.return_value.get_storage_server_resource.return_value = False
        self.setup_script.execute()
        mock_sandboxbase.return_value.clear_all_resources_live_status.assert_called_with(
            ['Generic TFTP server', 'Config Set Pool', 'Generic FTP server', 'netscout switch 3912', 'Subnet-28',
             'Subnet-30', 'GitLab', 'SSID_Pool'])
        report_info_calls = [call('Beginning load configuration for resources'),
                             call('Clearing status indicators ', write_to_output_window=True),
                             call('Skipping load configuration. No storage resource associated with the blueprint ', write_to_output_window=True),
                             call('Sandbox setup finished.', write_to_output_window=True)]
        mock_sandboxbase.return_value.report_info.assert_has_calls(report_info_calls)

    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    @patch('sandbox_scripts.environment.setup.setup_resources.SandboxBase')
    @patch('sandbox_scripts.environment.setup.setup_resources.SaveRestoreManager')
    def test_qualierror_exception(self, mock_save, mock_sandboxbase, mock_api_session):
        mock_sandboxbase.return_value.get_storage_server_resource.return_value = False
        mock_sandboxbase.return_value.activate_all_routes_and_connectors.side_effect = QualiError(name='a',message='b')

        self.setup_script.execute()
        report_info_calls = [call('Beginning load configuration for resources'),
                             call('Clearing status indicators ', write_to_output_window=True),
                             call('Skipping load configuration. No storage resource associated with the blueprint ',
                                  write_to_output_window=True)]
        mock_sandboxbase.return_value.report_info.assert_has_calls(report_info_calls)

        report_info_calls = [call('Sandbox setup finished successfully')]
        mock_sandboxbase.return_value.report_info.asset_not_called(report_info_calls)
        self.setup_script.logger.error.assert_called_with('Setup failed. CloudShell error at a. Error is: b')

    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    @patch('sandbox_scripts.environment.setup.setup_resources.SandboxBase')
    @patch('sandbox_scripts.environment.setup.setup_resources.SaveRestoreManager')
    def test_general_exception(self, mock_save, mock_sandboxbase, mock_api_session):
        mock_sandboxbase.return_value.get_storage_server_resource.side_effect = Exception('error')
        self.setup_script.execute()
        report_info_calls = [call('Beginning load configuration for resources')]
        mock_sandboxbase.return_value.report_info.assert_has_calls(report_info_calls)

        report_info_calls = [call('Skipping load configuration. No storage resource associated with the blueprint ',
                                  write_to_output_window=True),
                             call('Sandbox setup finished successfully')]
        mock_sandboxbase.return_value.report_info.asset_not_called(report_info_calls)

        self.setup_script.logger.error.assert_called_with('Setup failed. Unexpected error:error')

if __name__ == '__main__':
    unittest.main()
