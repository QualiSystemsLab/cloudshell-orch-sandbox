from multiprocessing.pool import ThreadPool
from threading import Lock
from cloudshell.helpers.scripts import cloudshell_scripts_helpers as helpers
from cloudshell.api.cloudshell_api import *
from cloudshell.api.common_cloudshell_api import CloudShellAPIError
from cloudshell.core.logger.qs_logger import get_qs_logger
from remap_child_resources_constants import *
from sandbox_scripts.helpers.resource_helpers import *
from sandbox_scripts.profiler.env_profiler import profileit


class EnvironmentSetup(object):
    NO_DRIVER_ERR = "129"
    DRIVER_FUNCTION_ERROR = "151"

    def __init__(self):
        self.reservation_id = helpers.get_reservation_context_details().id
        self.logger = get_qs_logger(log_file_prefix="CloudShell Sandbox Setup",
                                    log_group=self.reservation_id,
                                    log_category='Setup')

    #@profileit(scriptName='Setup')
    def execute(self):
        api = helpers.get_api_session()
        resource_details_cache = {}

        api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                            message= 'Beginning sandbox setup')

        self._prepare_connectivity(api, self.reservation_id)

        reservation_details = api.GetReservationDetails(self.reservation_id)

        deploy_result = self._deploy_apps_in_reservation(api=api,
                                                         reservation_details=reservation_details)

        self._try_exeucte_autoload(api=api,
                                   deploy_result=deploy_result,
                                   resource_details_cache=resource_details_cache)

        # refresh reservation_details after app deployment if any deployed apps
        if deploy_result and deploy_result.ResultItems:
            reservation_details = api.GetReservationDetails(self.reservation_id)

        self._connect_all_routes_in_reservation(api=api,
                                                reservation_details=reservation_details,
                                                reservation_id=self.reservation_id,
                                                resource_details_cache=resource_details_cache)

        self._run_async_power_on_refresh_ip(api=api,
                                            reservation_details=reservation_details,
                                            deploy_results=deploy_result,
                                            resource_details_cache=resource_details_cache,
                                            reservation_id=self.reservation_id)

        self._configure_apps(api=api, reservation_id=self.reservation_id)

        self.logger.info("Setup for reservation {0} completed".format(self.reservation_id))
        #api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
        #                                   message='Sandbox setup finished successfully')

    def _prepare_connectivity(self, api, reservation_id):
        """
        :param CloudShellAPISession api:
        :param str reservation_id:
        """
        self.logger.info("Preparing connectivity for reservation {0}".format(self.reservation_id))
        api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                            message='Preparing connectivity')
        api.PrepareSandboxConnectivity(reservation_id)

    def _try_exeucte_autoload(self, api, deploy_result, resource_details_cache):
        """
        :param GetReservationDescriptionResponseInfo reservation_details:
        :param CloudShellAPISession api:
        :param BulkAppDeploymentyInfo deploy_result:
        :param (dict of str: ResourceInfo) resource_details_cache:
        :return:
        """

        if deploy_result is None:
            self.logger.info("No apps to discover")
            api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                                message='No apps to discover')
            return

        message_written = False

        for deployed_app in deploy_result.ResultItems:
            if not deployed_app.Success:
                continue
            deployed_app_name = deployed_app.AppDeploymentyInfo.LogicalResourceName

            resource_details = api.GetResourceDetails(deployed_app_name)
            resource_details_cache[deployed_app_name] = resource_details

            autoload = "true"
            autoload_param = get_vm_custom_param(resource_details, "autoload")
            if autoload_param:
                autoload = autoload_param.Value
            if autoload.lower() != "true":
                self.logger.info("Apps discovery is disabled on deployed app {0}".format(deployed_app_name))
                continue

            try:
                self.logger.info("Executing Autoload command on deployed app {0}".format(deployed_app_name))
                if not message_written:
                    api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                                        message='Apps are being discovered...')
                    message_written = True

                api.AutoLoad(deployed_app_name)

                # for devices that are autoloaded and have child resources attempt to call "Connect child resources"
                # which copies CVCs from app to deployed app ports.
                api.ExecuteCommand(self.reservation_id, deployed_app_name,
                                   TARGET_TYPE_RESOURCE,
                                   REMAP_CHILD_RESOURCES, [])

            except CloudShellAPIError as exc:
                if exc.code not in (EnvironmentSetup.NO_DRIVER_ERR,
                                    EnvironmentSetup.DRIVER_FUNCTION_ERROR,
                                    MISSING_COMMAND_ERROR):
                    self.logger.error(
                        "Error executing Autoload command on deployed app {0}. Error: {1}".format(deployed_app_name,
                                                                                                  exc.rawxml))
                    api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                                        message='Discovery failed on "{0}": {1}'
                                                        .format(deployed_app_name, exc.message))

            except Exception as exc:
                self.logger.error("Error executing Autoload command on deployed app {0}. Error: {1}"
                                  .format(deployed_app_name, str(exc)))
                api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                                    message='Discovery failed on "{0}": {1}'
                                                    .format(deployed_app_name, exc.message))

    def _deploy_apps_in_reservation(self, api, reservation_details):
        apps = reservation_details.ReservationDescription.Apps
        if not apps or (len(apps) == 1 and not apps[0].Name):
            self.logger.info("No apps found in reservation {0}".format(self.reservation_id))
            api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                                message= 'No apps to deploy')
            return None

        app_names = map(lambda x: x.Name, apps)
        app_inputs = map(lambda x: DeployAppInput(x.Name, "Name", x.Name), apps)

        api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                            message= 'Apps deployment started')
        self.logger.info(
            "Deploying apps for reservation {0}. App names: {1}".format(reservation_details, ", ".join(app_names)))

        res = api.DeployAppToCloudProviderBulk(self.reservation_id, app_names, app_inputs)

        return res

    def _connect_all_routes_in_reservation(self, api, reservation_details, reservation_id, resource_details_cache):
        """
        :param CloudShellAPISession api:
        :param GetReservationDescriptionResponseInfo reservation_details:
        :param str reservation_id:
        :param (dict of str: ResourceInfo) resource_details_cache:
        :return:
        """
        connectors = reservation_details.ReservationDescription.Connectors
        endpoints = []
        for endpoint in connectors:
            if endpoint.State in ['Disconnected', 'PartiallyConnected', 'ConnectionFailed'] \
                    and endpoint.Target and endpoint.Source:
                endpoints.append(endpoint.Target)
                endpoints.append(endpoint.Source)

        if not endpoints:
            self.logger.info("No routes to connect for reservation {0}".format(self.reservation_id))
            return

        self.logger.info("Executing connect routes for reservation {0}".format(self.reservation_id))
        self.logger.debug("Connecting: {0}".format(",".join(endpoints)))
        api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                            message='Connecting all apps')
        res = api.ConnectRoutesInReservation(self.reservation_id, endpoints, 'bi')
        return res

    def _run_async_power_on_refresh_ip(self, api, reservation_details, deploy_results, resource_details_cache,
                                       reservation_id):
        """
        :param CloudShellAPISession api:
        :param GetReservationDescriptionResponseInfo reservation_details:
        :param BulkAppDeploymentyInfo deploy_results:
        :param (dict of str: ResourceInfo) resource_details_cache:
        :param str reservation_id:
        :return:
        """
        # filter out resources not created in this reservation
        resources = get_resources_created_in_res(reservation_details=reservation_details, reservation_id=reservation_id)
        if len(resources) == 0:
            api.WriteMessageToReservationOutput(
                reservationId=self.reservation_id,
                message='No resources to power on')
            self._validate_all_apps_deployed(deploy_results)
            return

        pool = ThreadPool(len(resources))
        lock = Lock()
        message_status = {
            "power_on": False,
            "wait_for_ip": False
        }

        async_results = [pool.apply_async(self._power_on_refresh_ip,
                                          (api, lock, message_status, resource, deploy_results, resource_details_cache))
                         for resource in resources]

        pool.close()
        pool.join()

        for async_result in async_results:
            res = async_result.get()
            if not res[0]:
                raise Exception("Reservation is Active with Errors - " + res[1])

        self._validate_all_apps_deployed(deploy_results)

    def _configure_apps(self, api, reservation_id):
        """
        :param CloudShellAPISession api:
        :param str reservation_id:
        :return:
        """
        self.logger.info('App configuration started ...')
        try:
            configuration_result = api.ConfigureApps(reservationId=reservation_id)

            if not configuration_result.ResultItems:
                api.WriteMessageToReservationOutput(reservationId=reservation_id, message='No apps to configure')
                return

            failed_apps = []
            for conf_res in configuration_result.ResultItems:
                if conf_res.Success:
                    message = "App '{0}' configured successfully".format(conf_res.AppName)
                    self.logger.info(message)
                else:
                    message = "App '{0}' configuration failed due to {1}".format(conf_res.AppName,
                                                                                 conf_res.Error)
                    self.logger.error(message)
                    failed_apps.append(conf_res.AppName)

            if not failed_apps:
                api.WriteMessageToReservationOutput(reservationId=reservation_id,
                                                    message='Apps were configured successfully.')
            else:
                api.WriteMessageToReservationOutput(reservationId=reservation_id, message=
                'Apps: {0} configuration failed. See logs for more details'.format(
                    ",".join(failed_apps)))
                raise Exception("Configuration of apps failed see logs.")
        except Exception as ex:
            self.logger.error("Error configuring apps. Error: {0}".format(str(ex)))
            raise

    def _validate_all_apps_deployed(self, deploy_results):
        if deploy_results is not None:
            for deploy_res in deploy_results.ResultItems:
                if not deploy_res.Success:
                    raise Exception("Reservation is Active with Errors - " + deploy_res.Error)

    def _power_on_refresh_ip(self, api, lock, message_status, resource, deploy_result, resource_details_cache):
        """
        :param CloudShellAPISession api:
        :param Lock lock:
        :param (dict of str: Boolean) message_status:
        :param ReservedResourceInfo resource:
        :param BulkAppDeploymentyInfo deploy_result:
        :param (dict of str: ResourceInfo) resource_details_cache:
        :return:
        """

        deployed_app_name = resource.Name
        deployed_app_data = None

        power_on = "true"
        wait_for_ip = "true"

        try:
            self.logger.debug("Getting resource details for resource {0} in reservation {1}"
                              .format(deployed_app_name, self.reservation_id))

            resource_details = get_resource_details_from_cache_or_server(api, deployed_app_name, resource_details_cache)
            # check if deployed app
            vm_details = get_vm_details(resource_details)
            if not hasattr(vm_details, "UID"):
                self.logger.debug("Resource {0} is not a deployed app, nothing to do with it".format(deployed_app_name))
                return True, ""

            auto_power_on_param = get_vm_custom_param(resource_details, "auto_power_on")
            if auto_power_on_param:
                power_on = auto_power_on_param.Value

            wait_for_ip_param = get_vm_custom_param(resource_details, "wait_for_ip")
            if wait_for_ip_param:
                wait_for_ip = wait_for_ip_param.Value

            # check if we have deployment data
            if deploy_result is not None:
                for data in deploy_result.ResultItems:
                    if data.Success and data.AppDeploymentyInfo.LogicalResourceName == deployed_app_name:
                        deployed_app_data = data
        except Exception as exc:
            self.logger.error("Error getting resource details for deployed app {0} in reservation {1}. "
                              "Will use default settings. Error: {2}".format(deployed_app_name,
                                                                             self.reservation_id,
                                                                             str(exc)))

        try:
            self._power_on(api, deployed_app_name, power_on, lock, message_status)
        except Exception as exc:
            self.logger.error("Error powering on deployed app {0} in reservation {1}. Error: {2}"
                              .format(deployed_app_name, self.reservation_id, str(exc)))
            return False, "Error powering on deployed app {0}".format(deployed_app_name)

        try:
            self._wait_for_ip(api, deployed_app_name, wait_for_ip, lock, message_status)
        except Exception as exc:
            self.logger.error("Error refreshing IP on deployed app {0} in reservation {1}. Error: {2}"
                              .format(deployed_app_name, self.reservation_id, str(exc)))
            return False, "Error refreshing IP deployed app {0}. Error: {1}".format(deployed_app_name, exc.message)

        return True, ""

    def _wait_for_ip(self, api, deployed_app_name, wait_for_ip, lock, message_status):
        if wait_for_ip.lower() == "true":

            if not message_status['wait_for_ip']:
                with lock:
                    if not message_status['wait_for_ip']:
                        message_status['wait_for_ip'] = True
                        api.WriteMessageToReservationOutput(
                            reservationId=self.reservation_id,
                            message='Waiting for apps IP addresses, this may take a while...')

            self.logger.info("Executing 'Refresh IP' on deployed app {0} in reservation {1}"
                             .format(deployed_app_name, self.reservation_id))

            api.ExecuteResourceConnectedCommand(self.reservation_id, deployed_app_name,
                                                "remote_refresh_ip",
                                                "remote_connectivity")
        else:
            self.logger.info("Wait For IP is off for deployed app {0} in reservation {1}"
                             .format(deployed_app_name, self.reservation_id))

    def _power_on(self, api, deployed_app_name, power_on, lock, message_status):
        if power_on.lower() == "true":
            self.logger.info("Executing 'Power On' on deployed app {0} in reservation {1}"
                             .format(deployed_app_name, self.reservation_id))

            if not message_status['power_on']:
                with lock:
                    if not message_status['power_on']:
                        message_status['power_on'] = True
                        api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                                            message='Apps are powering on...')

            api.ExecuteResourceConnectedCommand(self.reservation_id, deployed_app_name, "PowerOn", "power")
        else:
            self.logger.info("Auto Power On is off for deployed app {0} in reservation {1}"
                             .format(deployed_app_name, self.reservation_id))
