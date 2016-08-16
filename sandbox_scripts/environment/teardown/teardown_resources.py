# coding=utf-8
from sandbox_scripts.QualiEnvironmentUtils.Networking.NetworkingSaveNRestore import *
from cloudshell.core.logger import qs_logger
from sandbox_scripts.profiler.env_profiler import profileit


class EnvironmentTeardownResources:
    def __init__(self):
        self.reservation_id = helpers.get_reservation_context_details().id
        self.logger = qs_logger.get_qs_logger(log_file_prefix="CloudShell Sandbox Teardown Resources",
                                              log_group=self.reservation_id,
                                              log_category='Teardown')

    @profileit(scriptName="Teardown")
    def execute(self):
        sandbox = SandboxBase(self.reservation_id, self.logger)
        saveNRestoreTool = NetworkingSaveRestore(sandbox)

        sandbox.clear_all_resources_live_status()
        try:
            saveNRestoreTool.load_config(config_stage='Base', config_type='Running',
                                         ignore_models=['Generic TFTP server'])

        except QualiError as qe:
            self.logger.error("Teardown failed. " + str(qe))
        except:
            self.logger.error("Teardown failed. Unexpected error:" + str(sys.exc_info()[0]))
