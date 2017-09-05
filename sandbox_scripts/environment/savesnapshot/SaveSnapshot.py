# coding=utf-8
from cloudshell.helpers.scripts import cloudshell_scripts_helpers as helpers
from sandbox_scripts.QualiEnvironmentUtils.Sandbox import SandboxBase
from sandbox_scripts.helpers.Networking.save_restore_mgr import SaveRestoreManager
from cloudshell.core.logger.qs_logger import get_qs_logger
from sandbox_scripts.QualiEnvironmentUtils.QualiUtils import QualiError
import os, sys
import datetime

class EnvironmentSaveSnapshot:
    def __init__(self):
        self.reservation_id = helpers.get_reservation_context_details().id
        self.logger = get_qs_logger(log_file_prefix="SaveSnapshot",
                                    log_group=self.reservation_id,
                                    log_category='EnvironmentCommands')

    def execute(self):
        sandbox = SandboxBase(self.reservation_id, self.logger)
        saveNRestoreTool = SaveRestoreManager(sandbox)

        ignore_models=['Generic TFTP server', 'Config Set Pool', 'Generic FTP server', 'netscout switch 3912',
                       'Subnet-28', 'Subnet-30', 'GitLab', 'SSID_Pool' ]

        # why do this:  sandbox.clear_all_resources_live_status(ignore_models)
        try:
            username = helpers.get_reservation_context_details().owner_user
            if sandbox.get_storage_server_resource():
                #take first part of blueprint name up to first hyphen, underscore, or space
                snapshot_name = sandbox.Blueprint_name.replace('-', '_')
                snapshot_name = snapshot_name.replace(' ', '_').split('_')[0] + "_"
                snapshot_name += username + "_" + os.environ['name']
                sandbox.save_sandbox_as_blueprint(snapshot_name)
                sandbox.setcategorysnapshots(snapshot_name)
                sandbox.report_info("Blueprint " + snapshot_name + " created", write_to_output_window=True)
                #future feature when we have the api to update descriptions
                #description = Snapshot <snapshotname> of <origblueprintname> created <datetime>
                #description = "Snapshot of " + sandbox.Blueprint_name
                #description += " created " + datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")
                #sandbox.update_description(description)

                saveNRestoreTool.save_config(snapshot_name=snapshot_name, config_type='Running',
                                             ignore_models=ignore_models)
            else:
                 sandbox.report_error("There is no storage resource (e.g. FTP) available in the reservation",True,True)

        except QualiError as qe:
            self.logger.error("Save snapshot failed. " + qe.message)
            if "Name must contain only al" in qe.message:
                sys.tracebacklimit = 0
            raise Exception("Save snapshot failed. " + qe.message)
        except Exception as ex:
            blob = ex.message
            self.logger.error("Save snapshot. Unexpected error: " + str(sys.exc_info()))

