# coding=utf-8
from cloudshell.core.logger import qs_logger
from cloudshell.helpers.scripts import cloudshell_scripts_helpers as helpers
from sandbox_scripts.QualiEnvironmentUtils.Sandbox import SandboxBase
from sandbox_scripts.helpers.Networking.save_restore_mgr import SaveRestoreManager
from sandbox_scripts.QualiEnvironmentUtils.QualiUtils import QualiError
import sys

class EnvironmentTeardownResources:
    def __init__(self):
        self.reservation_id = helpers.get_reservation_context_details().id
        self.logger = qs_logger.get_qs_logger(log_file_prefix="CloudShell Sandbox Teardown Resources",
                                              log_group=self.reservation_id,
                                              log_category='Teardown')

    #@profileit(scriptName="Teardown")
    def execute(self):
        sandbox = SandboxBase(self.reservation_id, self.logger)
        saveNRestoreTool = SaveRestoreManager(sandbox)

        sandbox.report_info("Beginning load baseline configuration for resources (teardown)", write_to_output_window=True)
        ignore_models=['Generic TFTP server', 'Config Set Pool', 'Generic FTP server',
                               'netscout switch 3912', 'Subnet-28', 'Subnet-30', 'GitLab', 'SSID_Pool']
        sandbox.clear_all_resources_live_status(ignore_models)
        try:
            if saveNRestoreTool.get_storage_manager():
                ignore_models = ['Generic TFTP server', 'Config Set Pool', 'Generic FTP server',
                                 'netscout switch 3912', 'OnPATH Switch 3903', 'Ixia Traffic generator',
                                 "SubNet-28", "SubNet-30", "GitLab", 'SSID_Pool']
                saveNRestoreTool.load_config(config_stage='Base',
                                             config_type='Running',
                                             ignore_models=ignore_models,
                                             remove_temp_files=True,
                                             in_teardown_mode=True)
            else:
                sandbox.report_info("Skipping load configuration. No storage resource associated with the blueprint ",
                                    write_to_output_window=True)

            sandbox.report_info('Sandbox teardown finished successfully')

        except QualiError as qe:
            self.logger.error("Teardown failed. " + str(qe))
        except:
            self.logger.error("Teardown failed. Unexpected error:" + str(sys.exc_info()[0]))
