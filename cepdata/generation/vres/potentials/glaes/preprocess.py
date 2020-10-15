import geokit as gk
from datetime import datetime as dt
from osgeo import osr, ogr

from shapely.ops import unary_union
import shapely.wkt

from cepdata.generation.vres.potentials.glaes.create_priors import edgesByProximity, writeEdgeFile
from cepdata.geographics import get_shapes

from cepdata import data_path


def rasterize_natura_vector():
    """Create a rasterize version of the Natura2000 dataset"""

    potential_dir = f"{data_path}generation/vres/potentials/"
    natura = gk.vector.loadVector(f"{potential_dir}source/Natura2000/Natura2000_end2019_epsg3035.shp")
    extent = gk.Extent.fromVector(natura).castTo(3035).fit(100)
    extent.rasterize(natura, pixelWidth=100, pixelHeight=100, output=f"{potential_dir}generated/GLAES/natura2000.tif")


def create_shore_proximity_prior():
    """Generate a Prior, defined over offshore territories, indicating pixels
    which are less-than or equal-to X meters from shore"""

    # Indicates distances too close to shore (m)
    # considering values for 12, 30, 50, 60, 100, 150 and 200 nm (-> 22, 56, 93, 111, 185, 278 and 370 km)
    # distances = [0, 5e3, 10e3, 15e3, 20e3, 22e3, 25e3, 50e3, 56e3, 93e3, 100e3,
    #              111e3, 185e3, 200e3, 278e3, 300e3, 370e3, 400e3, 500e3, 1000e3]
    distances = [0, 20e3, 50e3, 100e3, 111e3, 185e3, 370e3, 500e3]

    # Create offshore shape
    countries = ["AL", "BA", "BE", "BG", "DE", "DK", "EE", "ES", "FI",
                 "FR", "GB", "GR", "HR", "IE", "IT", "LT", "LV", "ME",
                 "NL", "NO", "PL", "PT", "RO", "SE", "SI"]
    shapes = get_shapes(countries, which='offshore', save=True)
    offshore_union = unary_union(shapes["geometry"].values)

    poly_wkt = shapely.wkt.dumps(offshore_union)
    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromEPSG(4326)
    poly = ogr.CreateGeometryFromWkt(poly_wkt, spatial_ref)

    # Make Region Mask (set resolution to 1km)
    reg = gk.RegionMask.load(poly, pixelRes=1000)

    # Create a geometry list from the osm files
    potential_dir = f"{data_path}generation/vres/potentials/"
    gebco = gk.vector.loadVector(f"{potential_dir}source/GEBCO/GEBCO_2019/gebco_2019_n75.0_s30.0_w-20.0_e40.0.tif")
    indicated = reg.indicateValues(gebco, value='(0-]', applyMask=False) > 0.5
    geom = gk.geom.polygonizeMask(indicated, bounds=reg.extent.xyXY, srs=reg.srs)

    # Get edge matrix
    result = edgesByProximity(reg, [geom], distances)

    # Save result
    ftr_id = 0
    name = "shore_proximity"
    unit = "meters"
    description = "Indicates pixels which are less-than or equal-to X meters from shore"
    source = "GEBCO"
    tail = str(int(dt.now().timestamp()))
    output_dir = f"{potential_dir}generated/GLAES/"
    writeEdgeFile(result, reg, ftr_id, output_dir, name, tail, unit, description, source, distances)


def create_interior_shore_proximity_prior():
    """Generate a Prior, defined over onshore territories, indicating pixels
    which are less-than or equal-to X meters from shore"""

    # Indicates distances too close to shore (m)
    # considering values for 12, 30, 50, 60, 100, 150 and 200 nm (-> 22, 56, 93, 111, 185, 278 and 370 km)
    # distances = [0, 5e3, 10e3, 15e3, 20e3, 22e3, 25e3, 50e3, 56e3, 93e3, 100e3,
    #              111e3, 185e3, 200e3, 278e3, 300e3, 370e3, 400e3, 500e3, 1000e3]
    distances = [100, 250, 500, 1000, 1500]

    # Create onshore shape
    countries = ["AL", "AT", "BA", "BE", "BG", "CH", "CZ", "DE", "DK", "EE", "ES", "FI",
                 "FR", "GB", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "ME", "MK",
                 "NL", "NO", "PL", "PT", "RO", "RS", "SE", "SI", "SK"]

    shapes = get_shapes(countries, which='onshore')
    onshore_union = unary_union(shapes["geometry"].values)

    poly_wkt = shapely.wkt.dumps(onshore_union)
    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromEPSG(4326)
    poly = ogr.CreateGeometryFromWkt(poly_wkt, spatial_ref)

    # Make Region Mask (set resolution to 1km)
    reg = gk.RegionMask.load(poly, pixelRes=100)

    # Create a geometry list from the osm files
    from shapely.geometry import Polygon
    opposite = Polygon([(-20, 30), (-20, 75), (40, 75), (40, 30)]).difference(onshore_union)[0]
    from cepdata.geographics.plot import display_polygons
    display_polygons([opposite])
    poly_wkt_out_eu = shapely.wkt.dumps(opposite)
    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromEPSG(4326)
    poly_out_eu = ogr.CreateGeometryFromWkt(poly_wkt_out_eu, spatial_ref)
    target = osr.SpatialReference()
    target.ImportFromEPSG(3857)
    transform = osr.CoordinateTransformation(spatial_ref, target)
    poly_out_eu.Transform(transform)

    # Get edge matrix
    result = edgesByProximity(reg, [poly_out_eu], distances)

    # Save result
    ftr_id = 0
    name = "interior_shore_proximity"
    unit = "meters"
    description = "Indicates pixels which are less-than or equal-to X meters from shore inside shore"
    source = "NaturalEarth"
    tail = str(int(dt.now().timestamp()))
    potential_dir = f"{data_path}generation/vres/potentials/"
    output_dir = f"{potential_dir}generated/GLAES/"
    writeEdgeFile(result, reg, ftr_id, output_dir, name, tail, unit, description, source, distances)


if __name__ == '__main__':
    # rasterize_natura_vector()
    # create_shore_proximity_prior()
    create_interior_shore_proximity_prior()
