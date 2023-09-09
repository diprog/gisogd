#
# dividing a Polygon in (almost) equal parts using PyQGIS
# by Luisa Vieira Lucchese
# luisalucchese.com
# February 2022

# MIT License

#Copyright (c) 2022 Luisa V. Lucchese

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.

#
from qgis.core import *
import processing
#
# use split vector layer before running this code
# and refer to the blog post about this code to know how to use it
#
#### EDIT INPUTS BELOW ####
# provide the folder of the polygons below
POLYLOC='C:/.../'
POLYLOC_ID=POLYLOC+'id_'
# spacing of regular points
SPACING_REG=100.0
#number of divisions
N_DIV=3
# provide the folder to save the resulting points and polygons
OUTLOC='C:/.../'
OUTPOLYGONS=OUTLOC+'polygon_'
# coordinate system
CRS_PTS='EPSG:32722'
# min number and max number of id to process
MINNUM=1
MAXNUM=4
#################################################
for cycle in range(MINNUM,MAXNUM+1):
    try:
        # open
        polyloc_compose=POLYLOC_ID+str(cycle)+'.shp'
        poly_qgs = QgsVectorLayer(polyloc_compose, 'poly_id_'+str(cycle), 'ogr')
        QgsProject.instance().addMapLayers([poly_qgs])
        # extent of the polygon
        extentrect=poly_qgs.extent()
        xmax = extentrect.xMaximum()
        ymax = extentrect.yMaximum()
        xmin = extentrect.xMinimum()
        ymin = extentrect.yMinimum()
        extentreg=str(xmin) + ',' + str(xmax) + ','+ str(ymin)+ ',' + str(ymax)
        # generate regular points
        paramreg ={'EXTENT':extentreg, 'SPACING':SPACING_REG, 'INSET':5, 'RANDOMIZE':0, 'IS_SPACING':1, 'CRS': CRS_PTS, 'OUTPUT':'memory:'}
        regpoints=processing.run("qgis:regularpoints", paramreg)#temp
        # extract the points inside the polygons
        paramclip= {'INPUT': regpoints['OUTPUT'],'OVERLAY':poly_qgs, 'OUTPUT':'memory:'}
        regpointsclip=processing.run("native:clip", paramclip)#temp
        QgsProject.instance().addMapLayers([regpointsclip['OUTPUT']])
        # clustering
        paramcluster= {'CLUSTERS' : N_DIV, 'FIELD_NAME' : 'CLUSTER_ID','INPUT': regpointsclip['OUTPUT'],'OUTPUT':'memory:','SIZE_FIELD_NAME' : 'CLUSTER_SIZE'}
        regpointsclusters=processing.run("native:kmeansclustering", paramcluster)#temp
        # mean coordinates
        parammean= {'INPUT': regpointsclusters['OUTPUT'],'OUTPUT':'memory:','UID' : 'CLUSTER_ID', 'WEIGHT' : ''}
        regpointsmean=processing.run("native:meancoordinates", parammean)
        QgsProject.instance().addMapLayers([regpointsmean['OUTPUT']])
        # voronoi polygons
        paramvoro={'BUFFER' : 100, 'INPUT' : regpointsmean['OUTPUT'], 'OUTPUT' : 'memory:' }
        voronoi_poly=processing.run("qgis:voronoipolygons", paramvoro)
        QgsProject.instance().addMapLayers([voronoi_poly['OUTPUT']])
        # clip voronoi polygons by the original polygons
        paramclip= {'INPUT': voronoi_poly['OUTPUT'],'OVERLAY':poly_qgs, 'OUTPUT':OUTPOLYGONS+str(cycle)}
        polyclip=processing.run("native:clip", paramclip)
        polyclip_qgs = QgsVectorLayer(OUTPOLYGONS+str(cycle)+'.gpkg', 'divided_'+str(cycle))
        QgsProject.instance().addMapLayers([polyclip_qgs])
    except:
        print('the following polygon could not be processed:', cycle)