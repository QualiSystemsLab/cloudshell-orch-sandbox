# coding=utf-8
from sandbox_scripts.QualiEnvironmentUtils.Sandbox import *
import traceback


# ===================================
# ===================================
class ConfigFileManager:
    def __init__(self, sandbox):
        """
        :param SandboxBase sandbox:  The sandbox the config file mgr will work with
        """
        self.sandbox = sandbox

    # ----------------------------------
    # ----------------------------------
    def create_concrete_config_from_template(self, template_config_data, config_set_pool_data,
                                             resource):
        """
        Replace parameters in the template file with concrete values
        Parameters in the template file are marked with {}
        :param str template_config_data:  The data from the config template file
        :param dict config_set_pool_data:  A dictionary with the data from the config set pool
        :param ResourceBase resource:  The resource we want to create the config file for
        """
        try:
            concrete_config_data = template_config_data
            # Replace {ConfigPool.PARAM} with PARAM's value from the pool
            it = re.finditer(r"\{ConfigPool\.[^}]*\}", concrete_config_data)
            for match in it:
                param = match.group()
                concrete_config_data = concrete_config_data.replace(param, config_set_pool_data[param])

            # Replace {Device.Self.Address} with the resource's management ip
            concrete_config_data = concrete_config_data.replace('{Device.Self.Address}', resource.address)
            # Replace {Device.Self.ATTRIBUTE_NAME} with the resource's attribute value
            it = re.finditer(r"\{Device.Self\.[^}]*\}", concrete_config_data)
            for match in it:
                param = match.group()
                param_val = resource.get_attribute(param)
                concrete_config_data = concrete_config_data.replace(param, param_val)

            # TODO - Implement replacemant of params from types: {Device.NAME.Attribute_name}

            return concrete_config_data
        except:
            self.sandbox.report_error("Failed to create a concrete config file from the template\'s data. "
                                      "Unexpected error: " + traceback.format_exc())
