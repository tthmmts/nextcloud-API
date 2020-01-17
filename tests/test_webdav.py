import os
from requests.utils import quote

from .base import BaseTestCase, LocalNxcUserMixin
from nextcloud.api_wrappers import WebDAV


class TestWebDAV(LocalNxcUserMixin, BaseTestCase):

    CREATED_CODE = 201
    NO_CONTENT_CODE = 204
    MULTISTATUS_CODE = 207
    ALREADY_EXISTS_CODE = 405
    PRECONDITION_FAILED_CODE = 412

    COLLECTION_TYPE = 'collection'

    def create_and_upload_file(self, file_name, file_content, timestamp=None):
        with open(file_name, "w") as f:
            f.write(file_content)
        file_local_path = os.path.abspath(file_name)
        return self.nxc_local.upload_file(self.user_username, file_local_path, file_name, timestamp)

    def test_list_folders(self):
        res = self.nxc_local.list_folders(self.user_username)
        assert res.is_ok
        assert isinstance(res.data, list)
        assert isinstance(res.data[0], dict)
        res = self.nxc_local.list_folders(self.user_username, all_properties=True)
        assert res.is_ok
        assert isinstance(res.data, list)
        assert isinstance(res.data[0], dict)

    def test_upload_download_file(self):
        file_name = "test_file"
        file_content = "test file content"
        file_local_path = os.path.join(os.getcwd(), file_name)
        res = self.create_and_upload_file(file_name, file_content)
        # check status code
        assert res.is_ok
        assert res.raw.status_code == self.CREATED_CODE

        # test uploaded file can be found with list_folders
        file_nextcloud_href = os.path.join(WebDAV.API_URL, self.user_username, file_name)
        folder_info = self.nxc_local.list_folders(self.user_username, path=file_name)
        assert folder_info.is_ok
        assert len(folder_info.data) == 1
        assert isinstance(folder_info.data[0], dict)
        # check href
        assert folder_info.data[0]['href'] == file_nextcloud_href

        # remove file on local machine
        os.remove(file_local_path)
        self.nxc_local.download_file(self.user_username, file_name)
        # test file is downloaded to current dir
        assert file_name in os.listdir(".")
        with open(file_local_path, 'r') as f:
            downloaded_file_content = f.read()
        assert downloaded_file_content == file_content

        # delete file
        self.nxc_local.delete_path(self.user_username, file_name)
        os.remove(file_local_path)

    def test_upload_download_file_with_timestamp(self):
        file_name = "test_file"
        file_content = "test file content"
        file_local_path = os.path.join(os.getcwd(), file_name)

        # 2001-09-09T01:46:40 (UTC & GMT)
        timestamp = 1000000000

        res = self.create_and_upload_file(file_name, file_content, timestamp)

        # check status code
        assert res.is_ok
        assert res.raw.status_code == self.CREATED_CODE

        # test uploaded file can be found with list_folders
        file_nextcloud_href = os.path.join(WebDAV.API_URL, self.user_username, file_name)
        folder_info = self.nxc_local.list_folders(self.user_username, path=file_name)

        assert folder_info.is_ok
        assert len(folder_info.data) == 1
        assert isinstance(folder_info.data[0], dict)
        # check href
        assert folder_info.data[0]['href'] == file_nextcloud_href
        # test timestamp of uploaded file
        assert folder_info.data[0]["last_modified"] == "Sun, 09 Sep 2001 01:46:40 GMT"

        # remove file on local machine
        os.remove(file_local_path)
        self.nxc_local.download_file(self.user_username, file_name)

        # test file is downloaded to current dir
        assert file_name in os.listdir(".")
        with open(file_local_path, 'r') as f:
            downloaded_file_content = f.read()
        assert downloaded_file_content == file_content

        # test timestamp of downloaded file
        downloaded_file_timestamp = os.path.getmtime(file_local_path)
        assert downloaded_file_timestamp == timestamp

        # delete file
        self.nxc_local.delete_path(self.user_username, file_name)
        os.remove(file_local_path)

    def test_create_folder(self):
        folder_name = "test folder5"
        res = self.nxc_local.create_folder(self.user_username, folder_name)
        assert res.is_ok
        assert res.raw.status_code == self.CREATED_CODE

        # test uploaded file can be found with list_folders
        file_nextcloud_href = quote(os.path.join(WebDAV.API_URL, self.user_username, folder_name)) + "/"
        folder_info = self.nxc_local.list_folders(self.user_username, path=folder_name)
        assert folder_info.is_ok
        assert len(folder_info.data) == 1
        assert isinstance(folder_info.data[0], dict)
        # check href
        assert folder_info.data[0]['href'] == file_nextcloud_href
        # check that created file type is a collection
        assert folder_info.data[0]['resource_type'] == self.COLLECTION_TYPE

        nested_folder_name = "test folder5/nested/folder"
        res = self.nxc_local.assure_tree_exists(self.user_username, nested_folder_name)
        folder_info = self.nxc_local.list_folders(self.user_username, path=nested_folder_name)
        assert folder_info.is_ok
        assert len(folder_info.data) == 1

        # check 405 status code if location already exists
        res = self.nxc_local.create_folder(self.user_username, folder_name)
        assert not res.is_ok
        assert res.raw.status_code == self.ALREADY_EXISTS_CODE

        # delete folder
        res = self.nxc_local.delete_path(self.user_username, folder_name)
        assert res.is_ok
        assert res.raw.status_code == self.NO_CONTENT_CODE

    def test_delete_path(self):
        # test delete empty folder
        new_path_name = "path_to_delete"
        self.nxc_local.create_folder(self.user_username, new_path_name)
        res = self.nxc_local.delete_path(self.user_username, new_path_name)
        assert res.raw.status_code == self.NO_CONTENT_CODE
        assert res.is_ok
        res = self.nxc_local.list_folders(self.user_username, new_path_name)
        assert res.data is None

        # test delete file
        # create file at first
        file_name = "test_file"
        file_content = "test file content"
        with open(file_name, "w") as f:
            f.write(file_content)
        file_local_path = os.path.abspath(file_name)
        self.nxc_local.upload_file(self.user_username, file_local_path, file_name)
        # delete file
        res = self.nxc_local.delete_path(self.user_username, file_name)
        assert res.raw.status_code == self.NO_CONTENT_CODE
        assert res.is_ok
        res = self.nxc_local.list_folders(self.user_username, new_path_name)
        assert res.data is None

        # test delete nonexistent file
        res = self.nxc_local.delete_path(self.user_username, file_name)
        assert res.raw.status_code == self.NOT_FOUND_CODE
        assert not res.is_ok

    def test_copy_path(self):
        # create a file to copy
        file_name = "test_file"
        file_content = "test file content"
        self.create_and_upload_file(file_name, file_content)

        # copy file
        destination_path = "new_test_file_location"
        res = self.nxc_local.copy_path(self.user_username, file_name, destination_path)
        assert res.raw.status_code == self.CREATED_CODE
        assert res.is_ok
        # check both file exist
        original_file_props = self.nxc_local.list_folders(self.user_username, file_name)
        copy_props = self.nxc_local.list_folders(self.user_username, destination_path)
        assert len(original_file_props.data) == 1
        assert len(copy_props.data) == 1

        # copy file to already exist location
        # create new file
        new_file_name = 'test_file_2'
        new_file_content = 'test_file_3'
        self.create_and_upload_file(new_file_name, new_file_content)
        res = self.nxc_local.copy_path(self.user_username, file_name, new_file_name)
        assert not res.is_ok
        assert res.raw.status_code == self.PRECONDITION_FAILED_CODE
        # copy with overriding
        res = self.nxc_local.copy_path(self.user_username, file_name, new_file_name, overwrite=True)
        assert res.is_ok
        assert res.raw.status_code == self.NO_CONTENT_CODE

        # download just copied file and check content
        os.remove(os.path.join(os.getcwd(), new_file_name))  # remove file locally to download it
        self.nxc_local.download_file(self.user_username, new_file_name)
        with open(new_file_name, 'r') as f:
            downloaded_file_content = f.read()
        assert downloaded_file_content == file_content
        assert downloaded_file_content != new_file_content

    def test_move_path(self):
        # create a file to move
        file_name = "test_move_file 🇳🇴 😗 🇫🇴 🇦🇽"
        file_content = "test move file content 🇳🇴 😗 🇫🇴 🇦🇽"
        self.create_and_upload_file(file_name, file_content)

        # move file
        destination_path = "new_test_move_file_location 🇳🇴 😗 🇫🇴 🇦🇽"
        res = self.nxc_local.move_path(self.user_username, file_name, destination_path)
        assert res.is_ok
        assert res.raw.status_code == self.CREATED_CODE
        # check only new file exist
        original_file_props = self.nxc_local.list_folders(self.user_username, file_name)
        moved_file = self.nxc_local.list_folders(self.user_username, destination_path)
        assert original_file_props.data is None
        assert len(moved_file.data) == 1

        # copy file to already exist location

        # create a file to move
        file_name = "test_move_file 🇳🇴 😗 🇫🇴 🇦🇽"
        file_content = "test move file content 🇳🇴 😗 🇫🇴 🇦🇽"
        self.create_and_upload_file(file_name, file_content)

        # create new file for conflict
        new_file_name = 'test_move_file_ 🇳🇴 😗 🇫🇴 🇦🇽'
        new_file_content = 'test_move_file_ 🇳🇴 😗 🇫🇴 🇦🇽'
        self.create_and_upload_file(new_file_name, new_file_content)

        # move file to the new file location
        res = self.nxc_local.move_path(self.user_username, file_name, new_file_name)
        assert not res.is_ok
        assert res.raw.status_code == self.PRECONDITION_FAILED_CODE
        # move with overriding
        res = self.nxc_local.move_path(self.user_username, file_name, new_file_name, overwrite=True)
        assert res.is_ok
        assert res.raw.status_code == self.NO_CONTENT_CODE

        # download just copied file and check content
        os.remove(os.path.join(os.getcwd(), new_file_name))  # remove file locally to download it
        self.nxc_local.download_file(self.user_username, new_file_name)
        with open(new_file_name, 'r') as f:
            downloaded_file_content = f.read()
        assert downloaded_file_content == file_content
        assert downloaded_file_content != new_file_content

    def test_set_list_favorites(self):
        # create new file to make favorite
        file_name = "test_favorite"
        file_content = "test favorite content"
        self.create_and_upload_file(file_name, file_content)
        file_nextcloud_href = os.path.join(WebDAV.API_URL, self.user_username, file_name)

        # get favorites
        res = self.nxc_local.list_favorites(self.user_username)
        assert len(res.data) == 0

        # set file as favorite
        res = self.nxc_local.set_favorites(self.user_username, file_name)
        assert res.is_ok
        assert res.raw.status_code == self.MULTISTATUS_CODE

        # check file is in favorites
        res = self.nxc_local.list_favorites(self.user_username)
        assert res.is_ok
        assert len(res.data) == 1
        assert res.data[0]['href'] == file_nextcloud_href

