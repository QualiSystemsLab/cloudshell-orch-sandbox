# coding=utf-8
from sandbox_scripts.QualiEnvironmentUtils.Networking.NetworkingSaveNRestore import *
from cloudshell.helpers.scripts import cloudshell_scripts_helpers as helpers
from sandbox_scripts.profiler.env_profiler import profileit


class EnvironmentSaveSnapshot:
    def __init__(self):
        self.reservation_id = helpers.get_reservation_context_details().id
        self.logger = get_qs_logger(log_file_prefix="SaveSnapshot",
                                    log_group=self.reservation_id,
                                    log_category='EnvironmentCommands')

    @profileit(scriptName='SaveSnapshot')
    def execute(self):
        sandbox = SandboxBase(self.reservation_id, self.logger)
        saveNRestoreTool = NetworkingSaveRestore(sandbox)
        sandbox.clear_all_resources_live_status()
        try:
            if sandbox.get_tftp_resource():
                snapshot_name = os.environ['name']
                sandbox.save_sandbox_as_blueprint(snapshot_name)

                # replace spaces with _ in the snapshot's name
                snapshot_name = snapshot_name.replace(' ', '_')

                saveNRestoreTool.save_config(snapshot_name=snapshot_name, config_type='running',
                                             ignore_models=['Generic TFTP server'])
            else:
                sandbox.report_error("There is no TFTP resource available in the reservation",True,True)
        except QualiError as qe:
            self.logger.error("Save snapshot failed. " + str(qe))

        except:
            self.logger.error("Save snapshot. Unexpected error:" + str(sys.exc_info()))

