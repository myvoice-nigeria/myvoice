import requests

from django.conf import settings


class TextItException(Exception):
    pass


class TextItApiPermissionDenied(TextItException):
    """Raised when the API returns a 403 response."""
    pass


class TextItApiNotFound(TextItException):
    """Raised when the API returns a 404 response."""
    pass


class TextItApiBadRequest(TextItException):
    """Raised when the API returns a 400 response."""
    pass


class TextItApiClient(object):

    def __init__(self, token=None):
        super(TextItApiClient, self).__init__()
        self.token = token or settings.TEXTIT_API_TOKEN
        assert bool(self.token)

    @property
    def session(self):
        session = requests.Session()
        session.headers['Authorization'] = 'Token {0}'.format(self.token)
        return session

    def delete(self, endpoint, **kwargs):
        """Send a DELETE request to a standard TextIt endpoint."""
        url = TextItApiClient.get_api_url(endpoint)
        return self.request('delete', url, **kwargs)

    def get(self, endpoint, **kwargs):
        """Send a GET request to a standard TextIt endpoint."""
        url = TextItApiClient.get_api_url(endpoint)
        return self.request('get', url, **kwargs)

    @classmethod
    def get_api_url(cls, endpoint):
        """Build the full API url from a standard endpoint."""
        return 'https://api.textit.in/api/v1/{0}.json'.format(endpoint)

    def post(self, endpoint, **kwargs):
        """Send a POST request to a standard TextIt endpoint."""
        url = TextItApiClient.get_api_url(endpoint)
        return self.request('post', url, **kwargs)

    def request(self, method, url, **kwargs):
        """
        Send a get, post, or delete request to a URL using TextIt
        authorization details.
        """
        if method not in ('get', 'post', 'delete'):
            raise Exception("Unsupported method: {0}".format(method))
        method_func = getattr(self.session, method)
        try:
            response = method_func(url, **kwargs)
        except Exception as e:
            raise TextItException(e)
        if response.status_code == 403:
            raise TextItApiPermissionDenied()
        elif response.status_code == 404:
            raise TextItApiNotFound()
        elif response.status_code == 400:
            raise TextItApiBadRequest()
        else:
            return response.json()


class TextItApi(object):

    def __init__(self, client=None):
        super(TextItApi, self).__init__()
        self.client = client or TextItApiClient()

    def get_runs_for_flow(self, flow_id):
        """Returns all runs for a flow with a given id.

        TextIt paginates results in groups of 10. This method will make
        multiple requests to retrieve all of the paginated results.
        """
        run_data = self.client.get('runs', params={'flow': flow_id})
        runs = run_data['results']
        while run_data['next']:
            run_data = self.client.request('get', run_data['next'])
            runs = runs + run_data['results']
        return runs

    def get_flow_export(self, flow_id):
        """One-off method to get flow export data. Does NOT use the API.

        Per Nic Pottier, this information is not yet stable enough to be part
        of the official API and is not guaranteed to be stable.
        """
        client = requests.session()
        client.get('https://textit.in/')  # Set cookies.
        headers = {'referer': 'https://textit.in/'}
        response = client.post('https://textit.in/users/login/', headers=headers, data={
            'username': settings.TEXTIT_USERNAME,
            'password': settings.TEXTIT_PASSWORD,
            'csrfmiddlewaretoken': client.cookies['csrftoken'],
        })
        if response.status_code != 200:
            raise TextItException("Login failed.")
        response = client.get('https://textit.in/flow/export/{0}/'.format(flow_id))
        if response.status_code != 200:
            raise TextItException("Unable to retrieve survey export.")
        try:
            return response.json()
        except:
            raise TextItException("Response data was not JSON.")
