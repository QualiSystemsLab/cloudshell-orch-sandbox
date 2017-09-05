# coding=utf-8
from sandbox_scripts.QualiEnvironmentUtils.StorageClients.TFTPClient import *
from sandbox_scripts.QualiEnvironmentUtils.StorageClients.FTPClient import *
from sandbox_scripts.QualiEnvironmentUtils.RepositoryClients.GitLabClient import *

class StorageManager(object):
    def __init__(self, sandbox ):
        """
        Check if there is an ip pool
        :param SandboxBase sandbox:  The sandbox the config file mgr will work with
        :param ResourceBase storage_resource:  The storage resource in the sandbox
        """
        self.sandbox = sandbox
        storage_resource = self.sandbox.get_storage_server_resource()
        self.storage_exist = False
        if storage_resource is not None:
            self.storage_exist = True
            self.storage_client = self._get_storage_client(storage_resource)
        self.repository_client = None

        repository_resource = self.sandbox.get_repository_server_resource()
        self.repo_exist = False
        if repository_resource is not None:
            self.repo_exist = True
            self.repository_client = self._get_repository_client(repository_resource)

    # ----------------------------------
    # ----------------------------------
    # def _get_storage_client(self, storage_resource):
    #    if storage_resource.model.lower() == 'generic tftp server':
    #        return TFTPClient(self.sandbox,storage_resource)
    #   elif storage_resource.model.lower() == 'generic ftp server':
    #        return FTPClient(self.sandbox,storage_resource)

    def _get_storage_client(self, storage_resource):
        if storage_resource.model.lower() == 'generic tftp server':
            return TFTPClient(self.sandbox,storage_resource)
        elif storage_resource.model.lower() == 'generic ftp server':
            return FTPClient(self.sandbox,storage_resource)

    # -----------------------------------
    # ----------------------------------
    def _get_repository_client(self, repository_resource):
        if repository_resource.model.lower() == 'gitlab':
            return GitLabClient(self.sandbox, repository_resource)

    # ----------------------------------
    # ----------------------------------
    def get_configs_root(self):
        cr = self.storage_client.get_configs_root()
        return cr

    # ----------------------------------
    # ----------------------------------
    def _is_template(self, file_path):
        """
            Executes a command
            :param str file_path: file path
            :rtype: Bool
        """
        if file_path.endswith('.tm'):
            return True
        return False

    # ----------------------------------
    # ----------------------------------
    def download(self, source, destination):
        """
            Download a file
            :param str source: source file path
            :param str destination: destination file path
        """
        #TODO download from git if exists in topo
        if self.repository_client is not None:
            #change the path header to git   from ftp...
            repo_path = source.replace(self.storage_client.get_configs_root(),'')
            # download from git directly to destination
            self.repository_client.download(repo_path, destination)
            if not self._is_template(source):
                # download to the destination, but also upload from git to the storage in the correlating path
                self.storage_client.upload(source,destination)
        else:
            self.storage_client.download(source,destination)

    # ----------------------------------
    # ----------------------------------
    def upload(self, destination, source):
        self.storage_client.upload(destination,source)

    # ----------------------------------
    # ----------------------------------
    def dir_exist(self, dir_name):
        return self.storage_client.dir_exist(dir_name)

    # ----------------------------------
    # ----------------------------------
    def create_dir(self,env_dir, write_to_output=True):
        self.storage_client.create_dir(env_dir, write_to_output)

    # ----------------------------------
    # ----------------------------------
    def rename_file(self, file_path, new_name):
        self.storage_client.rename_file(file_path, new_name)

    # ----------------------------------
    # ----------------------------------
    def delete(self, file_path):
        self.storage_client.delete(file_path)

    # ----------------------------------
    # ----------------------------------
    def create_src_file_on_storage(self,win_path,write_to_output=False):
        self.storage_client.create_src_file_on_storage(win_path, write_to_output)

    # ----------------------------------
    # ----------------------------------
    def save_artifact_info(self,saved_artifact_info,env_dir,dest_name,write_to_output=False):
        self.storage_client.save_artifact_info(saved_artifact_info,env_dir,dest_name,write_to_output)

    # ----------------------------------
    # ----------------------------------
    def download_artifact_info(self,root_folder,dest_name,write_to_output=False):
        self.storage_client.download_artifact_info(root_folder, dest_name,write_to_output)
