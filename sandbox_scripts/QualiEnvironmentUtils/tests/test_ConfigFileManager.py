import unittest
import time
from freezegun import freeze_time
from mock import patch, Mock, call
from sandbox_scripts.QualiEnvironmentUtils.Resource import ResourceBase
from sandbox_scripts.QualiEnvironmentUtils.QualiUtils import QualiError
from sandbox_scripts.QualiEnvironmentUtils.ConfigFileManager import ConfigFileManager


class ConfigFileManagerTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    # ================================================================
    # test create_concrete_config_from_template function
    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    def test_values_only_from_pool_when_pool_doesnt_have_the_attribute(self, mock_api_session):
        config_file_mgr = ConfigFileManager()

        sandbox = None
        rd = Mock()
        rd.Name = 'myresource'
        rd.Address = '1.2.3.4'
        rd.ChildResources = []
        rd.ResourceAttributes = []
        mock_api_session.return_value.GetResourceDetails = Mock(return_value=rd)
        resource = ResourceBase(resource_name='myresource')

        tmp_template_config_file_data = """
                {ConfigPool:Pool1}
            """

        config_set_pool_data = {}
        with self.assertRaises(QualiError) as e:
            config_file_mgr.create_concrete_config_from_template(
                tmp_template_config_file_data, config_set_pool_data, sandbox, resource)

        the_exception = e.exception
        self.assertEqual(str(the_exception),
                         "CloudShell error at ConfigFileManager. Error is: Failed to create concrete config "
                         "for myresource from template. "
                         "Unexpected error: Could not find attribute {configpool:pool1} in the config pool")

    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    def test_values_only_from_pool(self, mock_api_session):
        config_file_mgr = ConfigFileManager()

        sandbox = None
        resource = None

        tmp_template_config_file_data = """{ConfigPool:Pool1}"""

        config_set_pool_data = {
            '{configpool:pool1}': 'Pool1Val'
        }
        concrete_config_data = config_file_mgr.create_concrete_config_from_template(
            tmp_template_config_file_data, config_set_pool_data, sandbox, resource)

        self.assertTrue(len(concrete_config_data) > 0)
        self.assertEqual(concrete_config_data, "Pool1Val")

    def test_quali_notation(self):
        config_file_mgr = ConfigFileManager()

        sandbox = None
        resource = None

        tmp_template_config_file_data = """{QUALI NOTATION}"""

        config_set_pool_data = {}
        with freeze_time("2017-01-17 12:00:01"):
            concrete_config_data = config_file_mgr.create_concrete_config_from_template(
                tmp_template_config_file_data, config_set_pool_data, sandbox, resource)

        self.assertTrue(len(concrete_config_data) > 0)
        self.assertEqual(concrete_config_data, 'Built from template: 2017-Jan-17 12:00:01')

    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    def test_resource_name(self, mock_api_session):
        config_file_mgr = ConfigFileManager()

        rd = Mock()
        rd.Name = 'myresource'
        rd.Address = '1.2.3.4'
        rd.ChildResources = []
        rd.ResourceAttributes = []
        mock_api_session.return_value.GetResourceDetails = Mock(return_value=rd)
        resource = ResourceBase(resource_name='myresource')

        sandbox = None

        tmp_template_config_file_data = """{Device:Self:Name}"""

        config_set_pool_data = {}
        concrete_config_data = config_file_mgr.create_concrete_config_from_template(
            tmp_template_config_file_data, config_set_pool_data, sandbox, resource)

        self.assertTrue(len(concrete_config_data) > 0)
        self.assertEqual(concrete_config_data, "myresource")

    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    def test_resource_address(self, mock_api_session):
        config_file_mgr = ConfigFileManager()

        rd = Mock()
        rd.Name = 'myresource'
        rd.Address = '1.2.3.4'
        rd.ChildResources = []
        rd.ResourceAttributes = []
        mock_api_session.return_value.GetResourceDetails = Mock(return_value=rd)
        resource = ResourceBase(resource_name='myresource')

        sandbox = None

        tmp_template_config_file_data = """{Device:Self:Address}"""

        config_set_pool_data = {}
        concrete_config_data = config_file_mgr.create_concrete_config_from_template(
            tmp_template_config_file_data, config_set_pool_data, sandbox, resource)

        self.assertTrue(len(concrete_config_data) > 0)
        self.assertEqual(concrete_config_data, "1.2.3.4")

    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    def test_resource_attribute(self, mock_api_session):
        config_file_mgr = ConfigFileManager()

        rd = Mock()
        rd.Name = 'myresource'
        rd.Address = '1.2.3.4'
        attr1 = Mock()
        attr1.Name = 'Pool1'
        attr1.Value = 'Pool1Val'
        rd.ChildResources = []
        rd.ResourceAttributes = [attr1]
        mock_api_session.return_value.GetResourceDetails = Mock(return_value=rd)
        resource = ResourceBase(resource_name='myresource')

        sandbox = None

        tmp_template_config_file_data = """{Device:Self:Pool1}"""

        config_set_pool_data = {}
        concrete_config_data = config_file_mgr.create_concrete_config_from_template(
            tmp_template_config_file_data, config_set_pool_data, sandbox, resource)

        self.assertTrue(len(concrete_config_data) > 0)
        self.assertEqual(concrete_config_data, "Pool1Val")

    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    def test_attribute_from_other_resource_in_sandbox(self, mock_api_session):
        config_file_mgr = ConfigFileManager()

        rd = Mock()
        rd.Name = 'myresource'
        rd.Address = '1.2.3.4'
        attr1 = Mock()
        attr1.Name = 'Pool1'
        attr1.Value = 'Pool1Val'
        rd.ChildResources = []
        rd.ResourceAttributes = [attr1]
        mock_api_session.return_value.GetResourceDetails = Mock(return_value=rd)
        resource = ResourceBase(resource_name='myresource', resource_alias='OtherDevice')

        sandbox = Mock()
        sandbox.get_all_resources.return_value = [resource]

        tmp_template_config_file_data = """{Device:OtherDevice:Pool1}"""

        config_set_pool_data = {}
        concrete_config_data = config_file_mgr.create_concrete_config_from_template(
            tmp_template_config_file_data, config_set_pool_data, sandbox, resource)

        self.assertTrue(len(concrete_config_data) > 0)
        self.assertEqual(concrete_config_data, "Pool1Val")

    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    def test_attribute_from_other_resource_in_sandbox_not_found(self, mock_api_session):
        config_file_mgr = ConfigFileManager()

        rd = Mock()
        rd.Name = 'myresource'
        rd.Address = '1.2.3.4'
        attr1 = Mock()
        attr1.Name = 'Pool1'
        attr1.Value = 'Pool1Val'
        rd.ChildResources = []
        rd.ResourceAttributes = [attr1]
        mock_api_session.return_value.GetResourceDetails = Mock(return_value=rd)
        resource = ResourceBase(resource_name='myresource', resource_alias='OtherDevice')

        sandbox = Mock()
        sandbox.get_all_resources.return_value = [resource]

        tmp_template_config_file_data = """{Device:OtherDevice:Pool123}"""

        config_set_pool_data = {}
        with self.assertRaises(QualiError) as e:
            concrete_config_data = config_file_mgr.create_concrete_config_from_template(
                tmp_template_config_file_data, config_set_pool_data, sandbox, resource)

        the_exception = e.exception
        self.assertEqual(str(the_exception),
                         "CloudShell error at ConfigFileManager. "
                         "Error is: Failed to create concrete config for myresource from template. "
                         "Unexpected error: Could not find attribute 'Pool123' in resource 'myresource'")

    @patch('cloudshell.helpers.scripts.cloudshell_scripts_helpers.get_api_session')
    def test_attribute_from_other_resource_in_sandbox_resource_not_found(self, mock_api_session):
        config_file_mgr = ConfigFileManager()

        rd = Mock()
        rd.Name = 'myresource'
        rd.Address = '1.2.3.4'
        attr1 = Mock()
        attr1.Name = 'Pool1'
        attr1.Value = 'Pool1Val'
        rd.ChildResources = []
        rd.ResourceAttributes = [attr1]
        mock_api_session.return_value.GetResourceDetails = Mock(return_value=rd)
        resource = ResourceBase(resource_name='myresource', resource_alias='OtherDevice')

        sandbox = Mock()
        sandbox.get_all_resources.return_value = [resource]

        tmp_template_config_file_data = """{Device:OtherDevice2:Pool1}"""

        config_set_pool_data = {}
        with self.assertRaises(QualiError) as e:
            concrete_config_data = config_file_mgr.create_concrete_config_from_template(
                tmp_template_config_file_data, config_set_pool_data, sandbox, resource)

        the_exception = e.exception
        self.assertEqual(str(the_exception),
                         "CloudShell error at ConfigFileManager. Error is: Failed to create concrete config "
                         "for myresource from template. "
                         "Unexpected error: Could not find a resource with alias OtherDevice2; "
                         "likely missing from blueprint.")


if __name__ == '__main__':
    unittest.main()
