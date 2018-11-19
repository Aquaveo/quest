from quest.plugins import ToolBase
from quest import util
from quest.api import get_metadata, update_metadata
import rasterio
import subprocess

import param


class RstReprojection(ToolBase):
    _name = 'raster-reprojection'
    operates_on_datatype = ['raster', 'discrete-raster']

    dataset = util.param.DatasetSelector(default=None,
                                         doc="""Dataset to run tool on.""",
                                         filters={'datatype': 'raster'},
                                         )
    new_crs = param.String(default=None,
                           doc="""New coordinate reference system to project to""")

    def _run_tool(self):

        dataset = self.dataset

        # get metadata, path etc from first dataset, i.e. assume all datasets
        # are in same folder. This will break if you try and combine datasets
        # from different providers

        orig_metadata = get_metadata(dataset)[dataset]
        src_path = orig_metadata['file_path']

        if self.new_crs is None:
            raise ValueError("A new coordinated reference system MUST be provided")

        dst_crs = self.new_crs

        new_metadata = {
            'parameter': orig_metadata['parameter'],
            'datatype': orig_metadata['datatype'],
            'file_format': orig_metadata['file_format'],
            'intake_plugin': orig_metadata['intake_plugin'],
            'intake_args': orig_metadata['intake_args'],
        }

        new_dset, file_path, catalog_entry = self._create_new_dataset(
            old_dataset=dataset,
            ext='.tif',
            dataset_metadata=new_metadata,
        )

        # run filter
        with rasterio.open(src_path) as src:
            # write out tif file
            subprocess.check_output(['gdalwarp', src_path, file_path, '-s_srs', src.crs.to_string(), '-t_srs', dst_crs])

        with rasterio.open(file_path) as f:
            geometry = util.bbox2poly(f.bounds.left, f.bounds.bottom, f.bounds.right, f.bounds.top, as_shapely=True)
        update_metadata(catalog_entry, quest_metadata={'geometry': geometry.to_wkt()})

        return {'datasets': new_dset, 'catalog_entries': catalog_entry}
