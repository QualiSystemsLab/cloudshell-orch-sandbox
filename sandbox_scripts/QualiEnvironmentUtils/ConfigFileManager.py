# coding=utf-8
import traceback
import re
from time import gmtime, strftime
from sandbox_scripts.QualiEnvironmentUtils.QualiUtils import QualiError


# ===================================
# ===================================
class ConfigFileManager:
    def __init__(self):
        pass

    # ----------------------------------
    # ----------------------------------
    def create_concrete_config_from_template(self, template_config_data, config_set_pool_data, sandbox, resource):
        """
        Replace parameters in the template file with concrete values
        Parameters in the template file are marked with {}
        :param str template_config_data:  The data from the config template file
        :param dict config_set_pool_data:  A dictionary with the data from the config set pool
        :param SandboxBase sandbox:  The sandbox to get other resources values from
        :param ResourceBase resource:  The resource we want to create the config file for
        """
        # if resource is None:
        #     raise QualiError('')
        try:

            concrete_config_data = template_config_data
            subst_log = ""
            # Replace {ConfigPool.PARAM} with PARAM's value from the pool
            it = re.finditer(r'\{ConfigPool\:[^}]*\}', concrete_config_data, flags=re.IGNORECASE)
            for match in it:
                param = match.group()
                if param.lower() in config_set_pool_data:
                    concrete_config_data = concrete_config_data.replace(param, config_set_pool_data[param.lower()])
                    subst_log += param + ' = ' + config_set_pool_data[param.lower()] + '\n'
                else:
                    raise Exception('Could not find attribute ' + param.lower() + ' in the config pool')

            # Replace {QUALI-NOTATION} WITH A NOTE
            it = re.finditer(r'\{QUALI NOTATION\}', concrete_config_data, flags=re.IGNORECASE)
            for match in it:
                param = match.group()
                quali_note = 'Built from template: ' + strftime('%Y-%b-%d %H:%M:%S', gmtime())
                concrete_config_data = concrete_config_data.replace(param, quali_note)
                subst_log += param + ' = ' + quali_note + '\n'
            # Replace {Device.Self.Name} with the resource's name
            it = re.finditer(r'\{Device:Self:Name\}', concrete_config_data, flags=re.IGNORECASE)
            for match in it:
                param = match.group()
                concrete_config_data = concrete_config_data.replace(param, resource.name)
                subst_log += param + ' = ' + resource.name + '\n'
            # Replace {Device.Self.Address} with the resource's management ip
            it = re.finditer(r'\{Device:Self:Address\}', concrete_config_data, flags=re.IGNORECASE)
            for match in it:
                param = match.group()
                concrete_config_data = concrete_config_data.replace(param, resource.address)
                subst_log += param + ' = ' + resource.address + '\n'
            # Replace {Device.Self.ATTRIBUTE_NAME} with the resource's attribute value
            # TODO: Need to decode password attributes: Password, Enable Password, and SNMP Read Community
            it = re.finditer(r'\{Device:Self\:[^}]*\}', concrete_config_data, flags=re.IGNORECASE)
            for match in it:
                param = match.group()
                idx = param.rfind(':')+1
                att_name = param[idx:len(param)-1]
                param_val = resource.get_attribute(att_name)
                # param_val = resource.get_attribute(param)
                concrete_config_data = concrete_config_data.replace(param, param_val)
                subst_log += param + ' = ' + param_val + '\n'
            # Replacement of params from types: {Device:ALIAS:Attribute_name} WHERE ALIAS is at any structure level
            it = re.finditer(r'\{Device:[^}]*\}', concrete_config_data, flags=re.IGNORECASE)
            the_resources = None
            for match in it:
                param = match.group()
                junk, sb_alias, alias_attribname = param.split(":")
                alias_attribname = alias_attribname.replace("}", "")
                concrete_name = ''
                if the_resources is None:  # fetch once the resources
                    the_resources = sandbox.get_all_resources()
                for resource in the_resources:
                    if resource.alias == sb_alias:
                        concrete_name = resource.name
                        if resource.attribute_exist(alias_attribname):
                            param_val = resource.get_attribute(alias_attribname)
                        else:
                            raise Exception("Could not find attribute '{0}' in resource '{1}'".format(alias_attribname,
                                                                                                      resource.name))
                        concrete_config_data = concrete_config_data.replace(param, param_val)
                        subst_log += param + ' = ' + param_val + '\n'
                        break
                if concrete_name <= ' ':
                    raise Exception('Could not find a resource with alias ' + sb_alias + '; likely missing from blueprint.')

            return concrete_config_data  #, subst_log
        except Exception as ex:
            raise QualiError('ConfigFileManager', "Failed to create concrete config for " + resource.name +
                             " from template. Unexpected error: " + ex.message)

