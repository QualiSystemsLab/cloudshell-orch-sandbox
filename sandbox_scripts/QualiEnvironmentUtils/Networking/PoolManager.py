# coding=utf-8
from sandbox_scripts.QualiEnvironmentUtils.Sandbox import *
import re


class PoolManager(object):
    def __init__(self, sandbox, pool_resource):
        """
        Check if there is an ip pool
        :param SandboxBase sandbox:  The sandbox the config file mgr will work with
        :param ResourceBase pool_resource:  The pool resource in the sandbox
        """
        self.sandbox = sandbox
        self.pool_resource = pool_resource

    # -----------------------------------------
    # Walk over the sub-resources of the pool resource,
    # For each sub-resource in the pool, get the data from their attributes, and update it on the actual device
    # The device's alias in the sandbox will appear as a pool sub-resource,
    # optionally with a number concatenated at the end e.g. Gateway1
    # -----------------------------------------
    def push_data_from_pool_to_sandbox(self):
        message = ''
        sandbox_resources = self.sandbox.get_root_resources()
        # a list to mark which resources in the sandbox were already updated
        sandbox_resources_can_update = [True]*len(sandbox_resources)

        for resource_from_pool in self.pool_resource.details.ChildResources:
            split_name = resource_from_pool.Name.split('/')
            name_of_resource_from_pool = split_name[len(split_name)-1]
            found_resource_in_sandbox = False
            idx = 0
            # Find the resource_from_pool in the sandbox
            for sandbox_resource in sandbox_resources:
                # use a regular expression since the pool may contain resources with a running index at the
                # end of the name, that should match a generic alias for multiple resources in the sandbox.
                # This can be caused from an abstract with quantity>1
                # e.g. the pool has CC1, CC2. The sandbox has a CC X2

                pattern = sandbox_resource.alias + '\d*'
                found_pattern = re.search(pattern, name_of_resource_from_pool, flags=0)
                if found_pattern:
                    if sandbox_resources_can_update[idx]:
                        found_resource_in_sandbox = True
                        sandbox_resources_can_update[idx] = False
                        for attribute in resource_from_pool.ResourceAttributes:
                            sandbox_resource.set_attribute_value(attribute_name=attribute.Name,
                                                                 attribute_value=attribute.Value)
                        break
                idx += 1
            if not found_resource_in_sandbox:
                message += 'Resource ' + resource_from_pool.Name + ' is in the pool, but could not be found in the sandbox. Please check\n'
        if message != '':
            raise QualiError(name=self.sandbox.id, message=message)

    # -----------------------------------------
    # Create a dictionary that will hold the data from the pool
    # Key: Resource name.
    # Value: A dictionary of the pool's values for the specific resource
    # (Taken from the attributes on the sub-resource in the pool resource)
    # -----------------------------------------
    def pool_data_to_dict(self):
        pool_data_dict = dict()
        for attribute in self.pool_resource.attributes:
            pool_data_dict['{ConfigPool.' + attribute.Name + '}'] = attribute.Value
        for resource_from_pool in self.pool_resource.details.ChildResources:
            split_name = resource_from_pool.Name.split('/')
            name_of_resource_from_pool = split_name[len(split_name)-1]
            #resource_attributes_dict = dict()
            for attribute in resource_from_pool.ResourceAttributes:
                resource_dict_key = '{ConfigPool.' + name_of_resource_from_pool + '.' + attribute.Name + '}'
                #resource_attributes_dict[resource_dict_key] = attribute.Value
                pool_data_dict[resource_dict_key] = attribute.Value
        return pool_data_dict
