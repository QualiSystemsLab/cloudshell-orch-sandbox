# coding=utf-8
from sandbox_scripts.QualiEnvironmentUtils.Sandbox import *
from sandbox_scripts.QualiEnvironmentUtils.Networking.NetworkingSaveNRestore import *
from sandbox_scripts.QualiEnvironmentUtils.Networking.NetworkingHealthCheck import *
from sandbox_scripts.profiler.env_profiler import profileit


class EnvironmentSetupResources(object):
    def __init__(self):
        self.reservation_id = helpers.get_reservation_context_details().id
        self.logger = get_qs_logger(log_file_prefix="CloudShell Sandbox Setup Resources",
                                    log_group=self.reservation_id,
                                    log_category='Setup')

    @profileit(scriptName='Setup')
    def execute(self):
        sandbox = SandboxBase(self.reservation_id, self.logger)

        do_save_restore = True
        saveNRestoreTool = NetworkingSaveRestore(sandbox)
        healthCheckTool = NetworkingHealthCheck(sandbox)

        try:
            healthCheckTool.devices_health_check(write_to_output=True)

            if sandbox.get_tftp_resource():
                # TODO- Get the config set name from the orchestration's params
                config_set_name = ''
                if saveNRestoreTool.is_snapshot():
                    saveNRestoreTool.load_config(config_stage='Snapshots', config_type='Running',
                                                 ignore_models=['Generic TFTP server'])
                else:
                    saveNRestoreTool.load_config(config_stage='Gold', config_type='Running',
                                                 ignore_models=['Generic TFTP server', 'Config Set Pool'],
                                                 config_set_name=config_set_name)

            # call activate_all_routes_and_connectors
            sandbox.activate_all_routes_and_connectors()

            # Call routes_validation
            #   sandbox.routes_validation()
        except QualiError as qe:
            self.logger.error("Setup failed. " + str(qe))
        except:
            self.logger.error("Setup failed. Unexpected error:" + str(sys.exc_info()[0]))
