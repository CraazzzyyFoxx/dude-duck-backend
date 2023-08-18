from locust import HttpUser, task, between


class PerformanceTests(HttpUser):
    wait_time = between(1, 3)

    @task(1)
    def test(self):
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json',
                   'Authorization': 'Bearer 3hspCFUpXlt6TZEXTTmWYI_LBYJMRPPN8Z_X7DTSuhc'}
        self.client.get("/api/v1/users/@me", headers=headers)