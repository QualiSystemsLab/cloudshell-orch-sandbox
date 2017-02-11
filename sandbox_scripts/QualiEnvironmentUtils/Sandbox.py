# coding=utf-8
from Resource import *
from cloudshell.core.logger.qs_logger import *
from cloudshell.helpers.scripts import cloudshell_scripts_helpers as helpers
from os.path import *

SEVERITY_INFO = 20
SEVERITY_ERROR = 40


class SandboxBase(object):
    def __init__(self, reservation_id, logger):
        """
        Load the configuration from config files on the Blueprint's devices
        :param str reservation_id:  reservation id
        """
        try:
            self._logger = logger
            """:type : logging.Logger"""
            self.api_session = helpers.get_api_session()
            self.id = reservation_id
            self.Blueprint_name = helpers.get_reservation_context_details().environment_name

            full_path = None
            tp = self.api_session.GetActiveTopologyNames()

            for value in tp.Topologies:
                filename = basename(value)
                if filename == self.Blueprint_name:
                    full_path = value
                    break

            if full_path:
                self.blueprint_details = self.api_session.GetTopologyDetails(full_path)

        except:
            err = "Failed to initialize the Sandbox. Unexpected error:" + \
                  str(sys.exc_info()[0])
            self.report_error(error_message=err)

    # ----------------------------------
    # ----------------------------------
    def write_message_to_output(self, message, severity_level=SEVERITY_INFO):
        """
            Write a message to the output window
        """

        if severity_level == SEVERITY_INFO:
            self.api_session.WriteMessageToReservationOutput(self.id, message)
        elif severity_level == SEVERITY_ERROR:
                self.api_session.WriteMessageToReservationOutput(self.id, '<font color="red">' + message + '</font>')

    # ----------------------------------
    def report_error(self, error_message, raise_error=True, write_to_output_window=False):
        """
        Report on an error to the log file, output window is optional.There is also an option to raise the error up
        :param str error_message:  The error message you would like to present
        :param bool raise_error:  Do you want to throw an exception
        :param bool write_to_output_window:  Would you like to write the message to the output window
        """
        self._logger.error(error_message)
        if write_to_output_window:
            self.write_message_to_output(error_message, SEVERITY_ERROR)
        if raise_error:
            raise QualiError(self.id, error_message)

    # ----------------------------------
    def report_info(self, message, write_to_output_window=False):
        """
        Report information to the log file, output window is optional.
        :param str message:  The message you would like to present
        :param bool write_to_output_window:  Would you like to write the message to the output window?
        """
        self._logger.info(message)
        if write_to_output_window:
            self.write_message_to_output(message, SEVERITY_INFO)

    # ----------------------------------
    def get_root_resources(self):
        """
            Get the root resources
            :rtype: list[ResourceBase]
        """
        root_resources = []
        root_resources_names_dict = {}
        resources = self.api_session.GetReservationDetails(self.id).ReservationDescription.Resources
        topo_resources = self.api_session.GetReservationDetails(self.id).ReservationDescription.TopologiesReservedResources
        # Loop over all devices in the sandbox and add to a dictionary all root devices:
        for resource in resources:
            split_name = resource.Name.split('/')
            root_resources_names_dict[split_name[0]] = 1

        # instantiate a resource object for each root device
        for root_resource_name in root_resources_names_dict.keys():
            root_resource_alias = ''
            for topo_resource in topo_resources:
                if topo_resource.Name == root_resource_name:
                    root_resource_alias = topo_resource.Alias
                    break
            root_resources.append(ResourceBase(root_resource_name, root_resource_alias))

        return root_resources

    # ----------------------------------
    # ----------------------------------
    def clear_all_resources_live_status(self):
        """
            Clear the live status from all the devices
        """
        root_resources = self.get_root_resources()
        for resource in root_resources:
            self.api_session.SetResourceLiveStatus(resource.name, '')

    # ----------------------------------
    # ----------------------------------
    def get_details(self):
        """
            Retrieves all details and parameters for a specified Sandbox, including its resources, routes and route
            segments, topologies, and Sandbox conflicts.
        """
        try:
            return self.api_session.GetReservationDetails(self.id)
        except QualiError as qe:
            err = "Failed to get the Sandbox's details. " + str(qe)
            self.report_error(error_message=err)
        except:
            err = "Failed to get the Sandbox's details. Unexpected error: " + str(sys.exc_info()[0])
            self.report_error(error_message=err)

    # ----------------------------------
    # ----------------------------------
    def activate_all_routes_and_connectors(self, write_to_output=True):
        """
        Activate the routes in the topology
        """
        try:
            self.report_info(message="Connecting the connectors and routes", write_to_output_window=write_to_output)
            self.activate_connectors(write_to_output=False)
            self.activate_routes(write_to_output=False)
            self.report_info(message="Connectors and routes are connected", write_to_output_window=write_to_output)
        except CloudShellAPIError as error:
            err = "Failed to activate connectors and routes. " + error.message
            self.report_error(error_message=err, write_to_output_window=write_to_output)
        except:
            err = "Failed to activate connectors and routes. Unexpected error: " + str(sys.exc_info()[0])
            self.report_error(error_message=err, write_to_output_window=write_to_output)

    # ----------------------------------
    # ----------------------------------
    def activate_connectors(self, write_to_output=True):
        """
        Activate the connectors in the topology
        """
        try:
            self.report_info(message="Connecting the connectors", write_to_output_window=write_to_output)
            details = self.get_details()
            connectors = details.ReservationDescription.Connectors
            bi_endpoints = []
            for endpoint in connectors:
                if endpoint.State in ['Disconnected', 'PartiallyConnected', 'ConnectionFailed'] \
                        and endpoint.Target and endpoint.Source:
                    bi_endpoints.append(endpoint.Target)
                    bi_endpoints.append(endpoint.Source)
            if not bi_endpoints:
                self.report_info(message="No connectors to connect for reservation {0}".format(self.id))
                return
            self.api_session.ConnectRoutesInReservation(self.id, bi_endpoints, 'bi')
            self.report_info(message="Connectors connected", write_to_output_window=write_to_output)
        except CloudShellAPIError as error:
            err = "Failed to activate the connectors. " + error.message
            self.report_error(error_message=err, write_to_output_window=write_to_output)
        except:
            err = "Failed to activate the connectors. Unexpected error: " + str(sys.exc_info()[0])
            self.report_error(error_message=err, write_to_output_window=write_to_output)

    # ----------------------------------
    # ----------------------------------
    def activate_routes(self, write_to_output=True):
        """
        Activate the routes in the topology
        """
        try:
            self.report_info(message="Connecting routes", write_to_output_window=write_to_output)
            details = self.get_details()
            routes = details.ReservationDescription.RequestedRoutesInfo
            bi_endpoints = []
            uni_endpoints = []
            for route_endpoint in routes:
                if route_endpoint.Target and route_endpoint.Source:
                    if route_endpoint.RouteType == 'bi':
                        bi_endpoints.append(route_endpoint.Target)
                        bi_endpoints.append(route_endpoint.Source)
                    elif route_endpoint.RouteType == 'uni':
                        uni_endpoints.append(route_endpoint.Target)
                        uni_endpoints.append(route_endpoint.Source)

            if not bi_endpoints and not uni_endpoints:
                self.report_info(message="No routes to connect for reservation {0}".format(self.id))
                return
            if bi_endpoints:
                self.api_session.ConnectRoutesInReservation(self.id, bi_endpoints, 'bi')
            if uni_endpoints:
                self.api_session.ConnectRoutesInReservation(self.id, uni_endpoints, 'uni')
            self.report_info(message="Routes connected", write_to_output_window=write_to_output)
        except CloudShellAPIError as error:
            err = "Failed to activate routes. " + error.message
            self.report_error(error_message=err, write_to_output_window=write_to_output)
        except:
            err = "Failed to activate routes. Unexpected error: " + str(sys.exc_info()[0])
            self.report_error(error_message=err, write_to_output_window=write_to_output)

    # -----------------------------------------
    # -----------------------------------------
    def execute_command(self, commandName, commandInputs=[], printOutput=False):
        """
        Executes a command
        :param str commandName:  Command Name - Specify the name of the command.
        :param list[str] commandInputs:  Command Inputs - Specify a matrix of input names and values
        required for executing the command.
        :param bool printOutput:  Print Output - Defines whether to print the command output
         in the Sandbox command output window.
        :rtype: CommandExecutionCompletedResultInfo
        """
        try:
            return self.api_session.ExecuteTopologyCommand(reservationId=self.id, commandName=commandName,
                                                           parameterValues=commandInputs, printOutput=printOutput)

        except CloudShellAPIError as error:
            raise QualiError(self.id, error.message)

    # -----------------------------------------
    # -----------------------------------------
    def save_sandbox_as_blueprint(self, blueprint_name, write_to_output=True):
        snapshot_exist = True

        try:
            full_path = None
            tp = self.api_session.GetActiveTopologyNames()

            for value in tp.Topologies:
                filename = basename(value)
                if filename == blueprint_name:
                    full_path = value
                    break

            if full_path is None:
                snapshot_exist = False

        except CloudShellAPIError as error:
            err = "Failed to save sandbox as blueprint. " + error.message
            self.report_error(error_message=err, write_to_output_window=write_to_output)
        if snapshot_exist:
            err = "Blueprint " + blueprint_name + " already exist. Please select a different name."
            self.report_error(error_message=err, write_to_output_window=write_to_output)
        # save the current Sandbox as a new Blueprint with the given snapshot name
        self.api_session.SaveReservationAsTopology(self.id, topologyName=blueprint_name, includeInactiveRoutes=True)

    # -----------------------------------------
    # check if this resource originated from an abstract resource
    # -----------------------------------------
    def is_abstract(self, resource_alias):
        for abstract_resource in self.blueprint_details.AbstractResources:
                if resource_alias == abstract_resource.Alias:
                        return True
        return False

    # -----------------------------------------
    # Return the tftp resource of the sandbox, if found
    # -----------------------------------------
    def get_tftp_resource(self):
        root_resources = self.get_root_resources()
        for resource in root_resources:
                if resource.model.lower() == 'generic tftp server':
                    return resource
        return None

    # -----------------------------------------
    # Return the pool resource of the sandbox, if found
    #  -----------------------------------------
    def get_config_set_pool_resource(self):
        root_resources = self.get_root_resources()
        for resource in root_resources:
                if resource.model.lower() == 'config set pool':
                    return resource
        return None

