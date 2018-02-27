from .base import ProviderBase, SingleFileServiceBase, PublishBase
from hs_restclient import HydroShare, HydroShareAuthBasic
from shapely.geometry import Point, box
import pandas as pd
from getpass import getpass
from ..api.database import get_db, db_session
from ..api.metadata import get_metadata
import param
from ..util import param_util


class DDServiceBase(SingleFileServiceBase):

    def get_features(self, **kwargs):
        raise NotImplementedError()


class DDGeoService(DDServiceBase):
    service_name = 'dd_geo'
    display_name = 'Data Depot Geo Service'
    description = 'Data Depot is a repository for ERDC ERS.'
    service_type = 'geo-discrete'
    unmapped_parameters_available = True
    geom_type = 'Point'
    datatype = 'timeseries'
    geographical_areas = ['Worldwide']
    bounding_boxes = [
        [-180, -90, 180, 90],
    ]
    _parameter_map = {}

    def get_features(self, **kwargs):
        print("DDGeoService")
        try:
            auth = self.provider.auth
            self.hs = HydroShare(auth=auth, hostname='192.168.56.106', port=8000, verify=False, use_https=False)
        except:
            self.hs = HydroShare(hostname='192.168.56.106', port=8000, verify=False, use_https=False)

        results = list(self.hs.resources())

        features = pd.DataFrame(results)
        idx = features['coverages'].apply(lambda x: len([c for c in x if c['type'] != 'period']) > 0)
        features = features[idx]

        features['geometry'] = features['coverages'].apply(self.parse_coverages)
        features['service_id'] = features['resource_id'].apply(str)
        features.index = features['service_id']
        features.rename(columns={
            'resource_title': 'display_name',
            'bag_url': 'download url'
        }, inplace=True)
        features['filename'] = features['download url'].apply(lambda x: x.split('/')[-1])
        features['reserved'] = features.apply(
            lambda x: {'download_url': x['download url'],
                       'filename': x['filename'],
                       'file_format': 'zip',
                       }, axis=1)

        return features

    def parse_coverages(self, resource_row):
        geometry = None
        for coverage in resource_row:
            coverage_type = coverage.get('type')
            if coverage_type == 'point':
                geometry = Point(float(coverage.get('value').get('north')), float(coverage.get('value').get('east')))
            elif coverage_type == 'box':
                geometry = box(float(coverage.get('value').get('westlimit')),
                               float(coverage.get('value').get('southlimit')),
                               float(coverage.get('value').get('eastlimit')),
                               float(coverage.get('value').get('northlimit')))
        return geometry

class DDNormService(DDServiceBase):
    service_name = "dd_norm"
    display_name = "Data Depot Normal Service"
    description = 'Data Depot is a repository for ERDC ERS.'
    service_type = "norm-discrete"
    unmapped_parameters_available = True
    _parameter_map = {}

    def get_features(self, **kwargs):
        print("DDNormService")
        try:
            auth = self.provider.auth
            self.hs = HydroShare(auth=auth, hostname='192.168.56.106', port=8000, verify=False, use_https=False)
            print("We got something")
        except:
            self.hs = HydroShare(hostname='192.168.56.106', port=8000, verify=False, use_https=False)
            print("We didn't get something")

        results = list(self.hs.resources())
        print("Aaron")
        features = pd.DataFrame(results)
        features['service_id'] = features['resource_id'].apply(str)
        features.index = features['service_id']
        features.rename(columns={
            'resource_title': 'display_name',
            'bag_url': 'download url'
        }, inplace=True)
        features['filename'] = features['download url'].apply(lambda x: x.split('/')[-1])
        features['reserved'] = features.apply(
            lambda x: {'download_url': x['download url'],
                       'filename': x['filename'],
                       'file_format': 'zip',
                       }, axis=1)

        return features


class DDPublisher(PublishBase):
    publisher_name = "dd_normal"
    display_name = "Data Depot Publisher"
    description = "empty"

    title = param.String(default="example title", doc="Title of resource", precedence=1)
    abstract = param.String(default="example abstract",  precedence=2, doc="An description of the resource to be added to HydroShare.")
    keywords = param.List(precedence=3, doc="list of keyword strings to describe the resource")
    dataset = param_util.DatasetSelector(filters={'status': 'downloaded'}, precedence=4, doc="dataset to publish to HydroShare")

    def __init__(self, provider, **kwargs):
        super(DDPublisher, self).__init__(provider, **kwargs)

    def publish(self, options=None):

        try:
            auth = self.provider.auth
        except:
            raise ValueError('Provider does not exist in the database.')

        p = param.ParamOverrides(self, options)
        hs = HydroShare(auth=auth, hostname='134.164.253.116', port=443, use_https=True, verify=False)
        rtype = 'GenericResource'
        dataset_metadata = get_metadata(p.dataset)[p.dataset]
        fpath = dataset_metadata['file_path']
        metadata = dataset_metadata['metadata']
        resource_id = hs.createResource(rtype, p.title, resource_file=fpath, keywords=p.keywords, abstract=p.abstract, metadata=metadata)
        print("Resource ID: ", resource_id)


class DDProvider(ProviderBase):
    service_base_class = DDServiceBase
    publishers_list = [DDPublisher]
    display_name = 'Data Depot Services'
    description = 'Services avaliable through the ERDC Data Depot Server.'
    organization_name = 'U.S. Army Engineering Research and Development Center'
    organization_abbr = 'ERDC'

    @property
    def auth(self):
        return HydroShareAuthBasic(**self.credentials)

    def authenticate_me(self, **kwargs):

        username = input("Enter Username: ")
        password = getpass("Enter Password: ")

        try:
            auth = HydroShareAuthBasic(username=username, password=password)
            hs = HydroShare(auth=auth, hostname='192.168.56.106', port=8000, verify=False)
            hs.resources(count=1) # Assuming that if this doesn't grab a resource then it will error out in the try statement.
            db = get_db()
            with db_session:
                p = db.Providers.select().filter(provider=self.name).first()

                provider_metadata = {
                    'provider': self.name,
                    'username': username,
                    'password': password,
                }

                if p is None:
                    db.Providers(**provider_metadata)
                else:
                    p.set(**provider_metadata)

            return True

        except Exception as e:
            print("Credentials were invalid.")

        return False