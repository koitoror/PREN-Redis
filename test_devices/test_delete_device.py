from tests.base import BaseTestCase, CommonTestCases
from fixtures.devices.devices_fixtures import (
    delete_device_query,
    delete_device_response,
    query_with_non_existant_id
)

class TestDeleteDevices(BaseTestCase):
    def test_delete_device(self):
        CommonTestCases.admin_token_assert_in(
            self,
            delete_device_query,
            delete_device_response
        )

    def test_delete_device_with_non_existant_id(self):
        CommonTestCases.admin_token_assert_in(
            self,
            query_with_non_existant_id,
            "DeviceId not found"
        )
