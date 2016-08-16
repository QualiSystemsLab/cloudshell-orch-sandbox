# coding=utf-8
# __author__ = 'ayelet.a'
import sys
from cloudshell.helpers.scripts import cloudshell_scripts_helpers as helpers
from cloudshell.api.cloudshell_api import *
from cloudshell.api.common_cloudshell_api import *
from QualiUtils import *


class ResourceBase(object):
    def __init__(self, resource_name, resource_alias=''):
        if resource_name != "":
            self.api_session = helpers.get_api_session()
            self.details = self.api_session.GetResourceDetails(resource_name)
            self.name = self.details.Name
            self.address = self.details.Address
            self.commands = self.api_session.GetResourceCommands(resource_name).Commands
            self.attributes = self.details.ResourceAttributes
            # If there is an attribute named 'model' take its value (exist in shells), otherwise take the family's model
            try:
                self.model = self.get_attribute('Model')
            except QualiError:
                self.model = self.details.ResourceModelName

            self.alias = resource_alias

    # -----------------------------------------
    # -----------------------------------------
    def has_command(self, command_name):
        for command in self.commands:
            if command_name == command.Name:
                return True
        return False

    # -----------------------------------------
    # -----------------------------------------
    def get_attribute(self, attribute_name):
        attribute_name = attribute_name.lower()
        for attribute in self.attributes:
            if attribute.Name.lower() == attribute_name:
                return attribute.Value
        raise QualiError(self.name, "Attribute: " + attribute_name + " not found")

    # -----------------------------------------
    # -----------------------------------------
    def set_attribute_value(self, attribute_name, attribute_value):
        try:
            self.api_session.SetAttributeValue(resourceFullPath=self.name, attributeName=attribute_name,
                                               attributeValue=attribute_value)
        except CloudShellAPIError as error:
            raise QualiError(self.name, "Attribute: " + attribute_name + " not found. " + error.message)

    # -----------------------------------------
    # implement the command to get the neighbors and their ports
    # will return a dictionary of device's name and its port
    # -----------------------------------------
    def get_neighbors(self, reservation_id):
        """
        Launch the get_neighbors command on the device
        :param str reservation_id:  Reservation id.
        """
        # Run executeCommand with the getNeighbors command and its params (ConfigPath,RestoreMethod)
        try:
            self.execute_command(reservation_id, 'get_neighbors', printOutput=True)
        except QualiError as error:
            raise QualiError(self.name, "Failed to update neighbors: " + error.message)
        except:
            raise QualiError(self.name, "Failed to update neighbors. Unexpected error:" + str(sys.exc_info()[0]))

    # -----------------------------------------
    # -----------------------------------------
    def load_network_config(self, reservation_id, config_path, config_type, restore_method='Override'):
        """
        Load config from a configuration file on the device
        :param str reservation_id:  Reservation id.
        :param config_path:  The path to the config file
        :param config_type:  StartUp or Running
        :param restore_method:  Optional. Restore method. Can be Append or Override.
        """
        # Run executeCommand with the restore command and its params (ConfigPath,RestoreMethod)
        try:
            self.execute_command(reservation_id, 'Restore',
                                 commandInputs=[InputNameValue('src_Path', str(config_path)),
                                                InputNameValue('restore_method', str(restore_method)),
                                                InputNameValue('config_type', str(config_type))],
                                 printOutput=True)
        except QualiError as qerror:
            raise QualiError(self.name, "Failed to load configuration: " + qerror.message)
        except:
            raise QualiError(self.name, "Failed to load configuration. Unexpected error:" + str(sys.exc_info()[0]))

    # -----------------------------------------
    # -----------------------------------------
    def save_network_config(self, reservation_id, config_path, config_type):
        """
        Save config from the device
        :param str reservation_id:  Reservation id.
        :param config_path:  The path where to save the config file
        :param config_type:  StartUp or Running
        """
        # Run executeCommand with the restore command and its params (ConfigPath,RestoreMethod)
        try:

            config_name = self.execute_command(reservation_id, 'Save',
                                               commandInputs=[InputNameValue('source_filename', str(config_type)),
                                                              InputNameValue('destination_host', str(config_path))],
                                               printOutput=True)

            # check the output is the created file name

        except QualiError as qerror:
            raise QualiError(self.name, "Failed to load configuration: " + qerror.message)
        except:
            raise QualiError(self.name, "Failed to load configuration. Unexpected error:" + str(sys.exc_info()[0]))

    # -----------------------------------------
    # -----------------------------------------
    # noinspection PyPep8Naming,PyDefaultArgument
    def execute_command(self, reservation_id, commandName, commandInputs=[], printOutput=False):
        """
        Executes a command
        :param str reservation_id:  Reservation id.
        :param str commandName:  Command Name - Specify the name of the command.
        :param list[InputNameValue] commandInputs:  Command Inputs - Specify a matrix of input names and values
        required for executing the command.
        :param bool printOutput:  Print Output - Defines whether to print the command output
         in the Sandbox command output window.
        :rtype: CommandExecutionCompletedResultInfo
        """
        # check the command exists on the device
        if self.commands.__sizeof__() > 0:
            # Run executeCommand with the restore command and its params (ConfigPath,RestoreMethod)
            try:
                return self.api_session.ExecuteCommand(reservation_id, self.name, 'Resource', commandName,
                                                       commandInputs, printOutput)
            except CloudShellAPIError as error:
                raise QualiError(self.name, error.message)

        else:
            raise QualiError(self.name, 'No commands were found')

    # -----------------------------------------
    # -----------------------------------------
    def set_address(self, address):
        self.api_session.UpdateResourceAddress(resourceFullPath=self.name, resourceAddress=address)


