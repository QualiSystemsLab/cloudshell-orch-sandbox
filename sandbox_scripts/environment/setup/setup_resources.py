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

    #@profileit(scriptName='Setup')
    def execute(self):
        sandbox = SandboxBase(self.reservation_id, self.logger)
        saveNRestoreTool = NetworkingSaveRestore(sandbox)

        try:
            sandbox.clear_all_resources_live_status()

            # Get the config set name from the orchestration's params
            config_set_name = ''
            try:
                config_set_name = os.environ['Set Name']
            except:
                pass
            ignore_models=['Generic TFTP server', 'Config Set Pool','Generic FTP server']
            if saveNRestoreTool.is_snapshot():
                saveNRestoreTool.load_config(config_stage='Snapshots', config_type='Running',
                                             ignore_models=ignore_models)
            else:
                saveNRestoreTool.load_config(config_stage='Gold', config_type='Running',
                                             ignore_models=ignore_models,
                                             config_set_name=config_set_name)

            # call activate_all_routes_and_connectors
            sandbox.activate_all_routes_and_connectors()

            # Call routes_validation
            #   sandbox.routes_validation()
        except QualiError as qe:
            self.logger.error("Setup failed. " + str(qe))
        except:
            self.logger.error("Setup failed. Unexpected error:" + str(sys.exc_info()[0]))