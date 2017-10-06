from sandbox_scripts.helpers.Networking.save_restore_mgr import SaveRestoreManager
from sandbox_scripts.QualiEnvironmentUtils.Sandbox import SandboxBase
from sandbox_scripts.QualiEnvironmentUtils.Resource import ResourceBase
from cloudshell.core.logger.qs_logger import get_qs_logger
from cloudshell.helpers.scripts import cloudshell_scripts_helpers as helpers
from multiprocessing.pool import ThreadPool
from threading import Lock
from sandbox_scripts.QualiEnvironmentUtils.QualiUtils import rsc_run_result_struct


class EnvironmentSetupVM(object):

    def __init__(self):
        self.reservation_id = helpers.get_reservation_context_details().id
        self.logger = get_qs_logger(log_file_prefix="CloudShell Sandbox Setup",
                                    log_group=self.reservation_id,
                                    log_category='Setup')

    # ----------------------------
    # ----------------------------
    def execute(self):
        self.sandbox = SandboxBase(self.reservation_id, self.logger)
        #TODO: don't use networking save and restore to figure if it's a snapshot setup
        self.is_snapshot = False
        save_n_restore_mgr = SaveRestoreManager(self.sandbox)
        if save_n_restore_mgr.get_storage_manager():
            if save_n_restore_mgr.is_snapshot():
                self.is_snapshot = True

        self.sandbox.report_info('Beginning VMs power on')
        self._run_async_power_on_refresh_ip()

    # ---------------------------
    # ---------------------------
    def _run_async_power_on_refresh_ip(self):
        # Get only VM resources
        resources = self.sandbox.get_root_vm_resources()

        if len(resources) == 0:
            self.sandbox.report_info(message='No VMs to power on ', write_to_output_window=True)
            return

        pool = ThreadPool(len(resources))
        lock = Lock()
        message_status = {
            "power_on": False,
            "wait_for_ip": False
            }
        async_results = [pool.apply_async(self._power_on_refresh_ip,
                                          (lock, message_status, resource))
                         for resource in resources]

        pool.close()
        pool.join()
        err_msg = ""
        for async_result in async_results:
            res = async_result.get()
            """:type : rsc_run_result_struct"""
            if not res.run_result:
                err_msg += "\n" + res.message
        if err_msg:
            self.sandbox.report_error("Reservation is Active with Errors - " + err_msg,raise_error=True)

    # ---------------------------
    # ---------------------------
    def _power_on_refresh_ip(self, lock, message_status, resource):
        """
        :param Lock lock:
        :param (dict of str: Boolean) message_status:
        :param ResourceBase resource:

        :return:
        """

        #deployed_app_name = resource.name
        run_result = rsc_run_result_struct(resource.name)
        power_on = "true"
        wait_for_ip = "true"

        if resource.model.lower() == "vcenter static vm":
            self.logger.debug("Resource {0} is a static app".format(resource.name))
            wait_for_ip = "false"
        elif not self.is_snapshot:
            return True, ""

        try:
            self._power_on(resource, power_on, lock, message_status)
        except Exception as exc:
            self.sandbox.report_error("Error powering on deployed app '{0}' in reservation '{1}'. Error: {2}"
                             .format(deployed_app_name, self.reservation_id, str(exc)),raise_error=False)
            run_result.message = str("Error powering on deployed app '{0}'").format(resource.name)
            run_result.run_result = False
            return run_result
        try:
            if wait_for_ip.lower() == "true":
                self._wait_for_ip(resource, lock, message_status)
            else:
                self.sandbox.report_info("Wait For IP is off for deployed app '{0}' in reservation '{1}'"
                                 .format(resource.name, self.reservation_id))
        except Exception as exc:
            self.sandbox.report_error("Error refreshing IP on deployed app '{0}' in reservation '{1}'. Error: {2}"
                              .format(resource.name, self.reservation_id, str(exc)),raise_error=False)
            run_result.message = str("Error refreshing IP deployed app '{0}'. Error: {1}").format(resource.name, exc.message)
            run_result.run_result = False


        return run_result

    # ---------------------------
    # ---------------------------
    def _wait_for_ip(self, resource, lock, message_status):
        if not message_status['wait_for_ip']:
            with lock:
                if not message_status['wait_for_ip']:
                    message_status['wait_for_ip'] = True
                    self.sandbox.report_info(message='Waiting for apps IP addresses, this may take a while...',
                                             write_to_output_window=True)

        self.sandbox.report_info("Executing 'Refresh IP' on deployed app '{0}' in reservation '{1}'"
                         .format(resource.name, self.reservation_id))
        with lock:
            resource.execute_connected_command(self.reservation_id,"remote_refresh_ip",
                                            "remote_connectivity")

    # ---------------------------
    # ---------------------------
    def _power_on(self, resource, power_on, lock, message_status):

        if power_on.lower() == "true":
            with lock:
                if not message_status['power_on']:
                    message_status['power_on'] = True
                    self.sandbox.report_info('Apps are powering on... ')

                self.sandbox.report_info(message="Executing 'Power On' on deployed app '{0}' "
                                         .format(resource.name),
                                         log_message="Executing 'Power On' on deployed app '{0}' in reservation '{1}'"
                                         .format(resource.name, self.reservation_id),
                                         write_to_output_window=True)
                resource.execute_connected_command(self.reservation_id,"PowerOn", "power")
        else:
            self.sandbox.report_info("Auto Power On is off for deployed app {0} in reservation {1}"
                                    .format(resource.name, self.reservation_id))

