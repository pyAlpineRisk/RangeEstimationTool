# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   Range-EstimationTool                            *
*   Nicole Kamp & Franz Langegger                                         *
*   Dezember 2020                                                             *
*                                                                         *
***************************************************************************
"""

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsProject,
                       QgsVectorLayer,
                       QgsTextFormat,
                       QgsExpression,
                       QgsFeatureRequest,
                       QgsFeature,
                       QgsGeometry,
                       QgsPoint,
                       QgsPointXY,
                       QgsVectorFileWriter,
                       QgsRasterBandStats,
                       QgsColorRampShader,
                       QgsRasterTransparency,
                       QgsFillSymbol,
                       QgsRasterShader,
                       QgsSingleBandPseudoColorRenderer,
                       QgsWkbTypes,
                       QgsVectorLayerSimpleLabeling,
                       QgsPalLayerSettings,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterFile,
                       QgsRasterLayer,
                       QgsCoordinateReferenceSystem,
                       QgsProcessingParameterFolderDestination,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterExtent,
                       QgsProcessingMultiStepFeedback,
                       QgsMessageLog)
from qgis import processing
from qgis.analysis import QgsRasterCalculatorEntry, QgsRasterCalculator
from qgis.PyQt.QtWidgets import QApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtGui import QColor
from qgis.utils import iface

from PIL import Image
Image.MAX_IMAGE_PIXELS = None
import osgeo.gdal as gdal
import numpy as np

from osgeo import ogr, osr
from shapely.geometry import Polygon
import matplotlib
import subprocess
from subprocess import call

import string, os, sys, copy, shutil, math, numpy, time, datetime
from time import *
from sys import *


#class ProjectUTM33N

#class AddSurfaceInfo

#class AddFields

#class LoopHeight


class RangeestimationProcessingAlgorithm(QgsProcessingAlgorithm):
    """
QGIS tool for determining range based on the flat-rate slope.
In- and Output-Parameters
    """
    INPUT_Shape = 'INPUT_SHP'
    INPUT_ALS = 'DGM'
    INPUT_prozent = 'PROZENT'
    #INPUT_extent = 'AUSSCHNITT'
    TEMP = 'TEMP'
    
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return RangeestimationProcessingAlgorithm()

    def name(self):
        return 'rangeestimationtool'

    def displayName(self):
        return self.tr('Range-estimation-Tool')

    def group(self):
        return self.tr('pyAlpineRisk')

    def groupId(self):
        return 'scripts'

    def shortHelpString(self):
        return self.tr("QGIS tool for determining range based on the flat-rate slope (Langegger&Kamp, 2021).")

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_Shape,
                self.tr('Anrisslinie'),
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_ALS,
                self.tr('Geländemodell'),
                #extension='tiff',
                #fileFilter="tiff (*.tif)",
                defaultValue='DEM.tif'
            )
        )

        self.addParameter(QgsProcessingParameterNumber(
            self.INPUT_prozent, 
            self.tr('Pauschalgefälle'),
            QgsProcessingParameterNumber.Double,
            30.0
            )
        )
              
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.TEMP, 
                self.tr('Output-Ordner'), 
                defaultValue='C:/temp/ST'
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        feedback = QgsProcessingMultiStepFeedback(1, feedback)
        results = {}
        outputs = {}
        
        laenge = 1000
        
        # Pfade definieren + Timestamp
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        temp_path = str(parameters[self.TEMP])+'/temp_'+str(timestamp)
        final_path = str(parameters[self.TEMP])+'/final_'+str(timestamp)
        
        
        if not os.path.exists(temp_path):
            os.makedirs(temp_path)
        if not os.path.exists(final_path):
            os.makedirs(final_path)
        
        #feedback.pushInfo(str(parameters[self.INPUT_extent]))


        ## Buffer
        buffer = out = temp_path + '/' + 'b1000.shp'
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': 700,
            'END_CAP_STYLE': 2,
            'INPUT': str(parameters[self.INPUT_Shape]),
            'JOIN_STYLE': 1,
            'MITER_LIMIT': 2,
            'SEGMENTS': 1,
            'OUTPUT': buffer
        }
        processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        ## Raster auf Layermaske zuschneiden
        out = temp_path + '/' + 'clip_vrt.tif'
        alg_params = {
            'ALPHA_BAND': False,
            'CROP_TO_CUTLINE': True,
            'DATA_TYPE': 0,
            'EXTRA': '',
            'INPUT': str(parameters[self.INPUT_ALS]),
            'KEEP_RESOLUTION': False,
            'MASK': str(buffer),
            'MULTITHREADING': False,
            'NODATA': None,
            'OPTIONS': '',
            'SET_RESOLUTION': False,
            'SOURCE_CRS': QgsCoordinateReferenceSystem('EPSG:31287'),
            'TARGET_CRS': QgsCoordinateReferenceSystem('EPSG:31287'),
            'X_RESOLUTION': None,
            'Y_RESOLUTION': None,
            'OUTPUT': out
        }
        processing.run('gdal:cliprasterbymasklayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        
        ## Cell Size
        raster_cs = gdal.Open(out)
        gt_cs =raster_cs.GetGeoTransform() 
        cs = gt_cs[1]
        
        del raster_cs
        del gt_cs
        
        # Geklipptes DGM öffnen
        dtm_clip_gdal = gdal.Open(out)
        format = "GTiff"
        driver = gdal.GetDriverByName( format )
        band1 = dtm_clip_gdal.GetRasterBand(1)
        im = Image.open(out)
        pix = im.load()
        gt = dtm_clip_gdal.GetGeoTransform()
        feedback.pushInfo(str(gt))
        width = dtm_clip_gdal.RasterXSize
        height = dtm_clip_gdal.RasterYSize
        minx = gt[0]
        miny = gt[3] + width*gt[4] + height*gt[5] 
        maxx = gt[0] + width*gt[1] + height*gt[2]
        maxy = gt[3]
        extent=str(minx)+","+str(maxx)+","+str(miny)+","+str(maxy)
        extent2=(minx,maxx,miny,maxy)
        feedback.pushInfo(str(extent))
        
        # Leere Grids anlegen
        grid_final = np.zeros(shape=(width,height), dtype=np.float32)
        grid_smooth = np.zeros(shape=(width,height), dtype=np.float32)
        grid_rcl = np.zeros(shape=(width,height), dtype=np.float32)
        
        
        ## 1. Höhe und Radius von Dreieck berechnen
        proz= 90-(parameters[self.INPUT_prozent])
        hoehe = math.cos((math.radians(proz)))*laenge
        r = math.sin((math.radians(proz)))*laenge
        feedback.pushInfo(str(hoehe))
        feedback.pushInfo(str(r))
 

        ## 2. Profil-Punkte aus einer Linie generieren
        #out1 = temp_path + '/' + 'out1.shp'
        #alg_params = {
        #    'DEM': str(out),
        #    'LINES': str(parameters[self.INPUT_Shape]),
        #    'NAME': 'profil',
        #    'SPLIT         ': True,
        #    'VALUES': [],
        #    'PROFILE': out1,
        #   'PROFILES': out1
        #}
        #processing.run('saga:profilesfromlines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        
        ## 2. Profil-Punkte aus einer Linie generieren (Extract vertices; Add raster values) 
        out1 = temp_path + '/' + 'out1.shp'
        out1_z = temp_path + '/' + 'out1_z.shp'
        alg_params = {
            'INPUT': str(parameters[self.INPUT_Shape]),
            'OUTPUT': out1
        }
        processing.run('qgis:extractvertices', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        alg_params = {
            'GRIDS': str(out),
            'RESAMPLING': 0,
            'SHAPES': out1,
            'RESULT': out1_z
        }
        processing.run('saga:addrastervaluestopoints', alg_params, context=context, feedback=feedback, is_child_algorithm=True)


        ## 3. Search Cursor
        vLayer = QgsVectorLayer(out1_z, "layer1", "ogr")
        features = vLayer.getFeatures()
        attr=[]
        fields = vLayer.fields()
        for feature in features:
            ## 3.1. Buffer
            value = feature[1]
            zvalue = feature[6]
            znew = zvalue - hoehe
            out2 = temp_path + '/' + 'out2_b'+str(value)+'.shp'
            txt = open(temp_path + '/' + 'xyz_' +str(value)+'.txt', "w")
            writer = QgsVectorFileWriter(out2,"UTF-8",fields,QgsWkbTypes.Polygon25D,vLayer.crs(),driverName="ESRI Shapefile")
            
            geom = feature.geometry()
            x, y = geom.asPoint()
            buffer = geom.buffer(r, 5)
            feature.setGeometry(buffer)
            writer.addFeature(feature)
            del(writer)
            
            ## 3.2. Set Z Value
            #out2_z = temp_path + '/' + 'out2_b'+str(value)+'_z.shp'
            #            
            #alg_params = {
            #    'INPUT': out2_z,
            #    'Z_VALUE':znew,
            #    'OUTPUT': out3
            #}
            #processing.run('qgis:setzvalue', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            
            ## 3.2. Extract vertices 
            out3 = temp_path + '/' + 'out3_b'+str(value)+'.shp'
            alg_params = {
                'INPUT': out2,
                'OUTPUT': out3
            }
            processing.run('qgis:extractvertices', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                       
            txt.write(str(x) + ", ")
            txt.write(str(y) + ", ")
            txt.write(str(zvalue) + "\n")
        
            ## 3.3. Search Cursor2
            vLayer2 = QgsVectorLayer(out3, "layer2", "ogr")
            features2 = vLayer2.getFeatures()
            attr2=[]
            fields2 = vLayer2.fields()
            for feature2 in features2:
            ## 3.3.1. Get X, Y, Z
                geom2 = feature2.geometry()
                x2, y2 = geom2.asPoint()
                        
                txt.write(str(x2) + ", ")
                txt.write(str(y2) + ", ")
                txt.write(str(znew) + "\n")
                
            txt.close()
        
            txt = open(temp_path + '/' + 'xyz_' +str(value)+'.txt', "r")
        
            ## 3.4. TXT to Point 3D
            out4 = temp_path + '/' + 'out4_'+str(value)+'.shp'
            driver = ogr.GetDriverByName('Esri Shapefile')
            ds = driver.CreateDataSource(out4)
            layer = ds.CreateLayer('', None, ogr.wkbPoint25D)
            layer.CreateField(ogr.FieldDefn('id', ogr.OFTInteger))
            defn = layer.GetLayerDefn()
            feat = ogr.Feature(defn)
            feat.SetField('id', 1)
        
            for i in txt:
                i=i.split(',')
                #i=i.strip('\n')
                xneu = float(i[0])
                yneu=float(i[1])
                zneu=float(i[2])

                geom = ogr.Geometry(ogr.wkbPoint25D)
                geom.AddPoint(xneu, yneu, zneu)
                feat.SetGeometry(geom)
                layer.CreateFeature(feat)
                    
            feat = geom = None 
            ds = layer = feat = geom = None 
        

            ## 3.5. Differenzmodell
            ## 3.5.1. Aus 3D Punkte Raster berechnen
            out5 = temp_path + '/' + 'out5_'+str(value)+'.tif'
 
            ## TIN
            alg_params = {
                'EXTENT': str(extent),
                'INTERPOLATION_DATA': str(out4) + '::~::1::~::-1::~::2',
                'METHOD': 0,
                'PIXEL_SIZE': int(cs),
                'OUTPUT': out5
            }
            processing.run('qgis:tininterpolation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        
            ## 3.6. Snap Raster
            out6 = temp_path + '/' + 'out6_'+str(value)+'.tif'
            flaeche3d = gdal.Open(out5)
            format = "GTiff"
            driver = gdal.GetDriverByName( format )
            OutTile = gdal.Warp(out6, flaeche3d,
                format=format, outputBounds=[minx, miny, maxx, maxy], 
                xRes=int(cs), yRes=int(cs))
            OutTile = None
       
            out7 = temp_path + '/' + 'out7_'+str(value)+'.tif'
            alg_params = {'INPUT_A' : str(out6),
                'BAND_A' : 1,
                'INPUT_B' : str(out),
                'BAND_B' : 1,
                'FORMULA' : '(A - B)',  
                'OUTPUT' : out7
            }
            processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True) 


            ## 3.7. Raster to Array
            old_rds = gdal.Open(out7)
            format = "GTiff"
            driver = gdal.GetDriverByName( format )
            band1 = old_rds.GetRasterBand(1)
            im = Image.open(out7)
            pix = im.load()

        
            # 3.8. Leeres Grid anlegen + Werte in Grids schreiben
            grid1 = np.zeros(shape=(width,height), dtype=np.float32)
        
            for row in range(0, width):
                for col in range(0, height):
                    val1 = pix[row, col]
                    #feedback.pushInfo(str(val1))
                    if val1 > 0 and val1 < 500:
                        nval = val1
                        #feedback.pushInfo(str(val1))
                        grid1[row,col]=nval
                        final_val = grid_final[row,col]
                        if final_val < nval:
                            grid_final[row,col]=nval
                    else:
                        nval2 = -9999.0
                        grid1[row,col]=nval2

        
        ## 4. Smooth Raster
        #for row in range(1, width-1):
        #    for col in range(1, height-1):
        #        count_v = 0
        #        val_old = grid_final[row, col]
        #        if val_old > -9999.0:
        #            count_v = val_old
        #            count_n = 1
        #            for rown in range(-2, 2):
        #                for coln in range(-2, 2):
        #                    n = grid_final[row+rown, col+coln]
        #                    if n > 0:
        #                        count_v = count_v + n
        #                        count_n = count_n + 2
        #            smooth_v = count_v/count_n
        #            grid_smooth[row, col]=smooth_v
        #        if val_old < 0:
        #            grid_smooth[row, col]=-9999.0
        
        
        ## Reclassify Raster
        for row in range(0, width):
            for col in range(0, height):
                val_old = grid_final[row, col]
                if val_old > 0:
                    grid_rcl[row, col]=1
                if val_old < 0:
                    grid_rcl[row, col]=0

        
        ## 5. Arrays to Rasters
        out9 = temp_path + '/' + 'out9.tif'
        out9_rcl = temp_path + '/' + 'out9_rcl.tif'
        
        grid_final=np.flip(grid_final,1)
        grid_final=np.rot90(grid_final)
        imsave = Image.fromarray(grid_final, mode='F')
        imsave.save(out9, "TIFF")
        
        del imsave
        
        #grid_smooth=np.flip(grid_smooth,1)
        #grid_smooth=np.rot90(grid_smooth)
        #imsave = Image.fromarray(grid_smooth, mode='F')
        #imsave.save(out9, "TIFF")
                
        grid_rcl=np.flip(grid_rcl,1)
        grid_rcl=np.rot90(grid_rcl)
        imsave = Image.fromarray(grid_rcl, mode='F')
        imsave.save(out9_rcl, "TIFF")
        
        del imsave

        
        ## 6. Raster georeferenzieren
        ## 6.1. Raster 1
        out10 = final_path + '/' + 'steinschlag_flaeche.tif'
        
        src_ds = gdal.Open(out9)
        format = "GTiff"
        driver = gdal.GetDriverByName( format )
                
        dst_ds = driver.CreateCopy(out10, src_ds, 0)
        dst_ds.SetGeoTransform(gt)
        epsg = 31287
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(epsg)
        dest_wkt = srs.ExportToWkt()
        dst_ds.SetProjection(dest_wkt)

        # Close files
        dst_ds = None
        src_ds = None

        ## 6.2. Raster 2        
        out10_rcl = temp_path + '/' + 'out10.tif'
        
        src_ds = gdal.Open(out9_rcl)
        format = "GTiff"
        driver = gdal.GetDriverByName( format )
                
        dst_ds = driver.CreateCopy(out10_rcl, src_ds, 0)
        dst_ds.SetGeoTransform(gt)
        epsg = 31287
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(epsg)
        dest_wkt = srs.ExportToWkt()
        dst_ds.SetProjection(dest_wkt)

        # Close files
        dst_ds = None
        src_ds = None
        
        
        ## 7. Raster in Polygon umwandeln
        out11 = final_path + '/' + 'flaeche.shp'
        src_ds = gdal.Open(out10_rcl)
        srcband = src_ds.GetRasterBand(1)
        driver = ogr.GetDriverByName('Esri Shapefile')
        ds = driver.CreateDataSource(out11)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(31287)
        dst_ds = ds.CreateLayer('', srs=srs)
        newField = ogr.FieldDefn('id', ogr.OFTInteger)
        #newField.SetPrecision(1)
        dst_ds.CreateField(newField)
        #newField2 = ogr.FieldDefn('flaeche', ogr.OFTReal)
        #dst_ds.CreateField(newField2)
        gdal.Polygonize(srcband, None, dst_ds, 0, [], callback=None)
        feat = geom = None 
        ds = dst_ds = feat = geom = None
        
        ## 7.1. Edit Vector
        vLayer = QgsVectorLayer(out11, "layer3", "ogr")
        features = vLayer.getFeatures()
        fields = vLayer.fields()
        vLayer.startEditing()
        for feature in features:
            id=feature['id']
            feedback.pushInfo(str(id))
            if id == 0:
                vLayer.deleteFeature(feature.id())
            #if id == 1:
                #geom = feature.geometry()
                #area2 = geom.area()
                #vLayer_provider=vLayer.dataProvider()
                #attr_value={1:area2}
                #vLayer_provider.changeAttributeValues({id:attr_value})
        vLayer.commitChanges()
            
        del feature
        

        ## 8. Add Layers
        root = QgsProject.instance().layerTreeRoot()
        mygroup = root.findGroup("Range-estimation-results")
        ## 8.1. Begrenzung
        layer = QgsVectorLayer(out11, "Begrenzung", "ogr")
        text_format = QgsTextFormat()
        #label = QgsPalLayerSettings()
        #label.fieldName = 'flaeche'
        #label.enabled = True
        #label.setFormat(text_format)
        #labeler = QgsVectorLayerSimpleLabeling(label)
        #layer.setLabelsEnabled(True)
        #layer.setLabeling(labeler)
        #layer.triggerRepaint()
        symbol = QgsFillSymbol.createSimple({'color':'255,0,0,0','color_border':'#000000','width_border':'0.6'})#({'line_style': 'dash', 'color': 'black'})
        layer.renderer().setSymbol(symbol)
        layer.triggerRepaint()
        QgsProject.instance().addMapLayer(layer, False)
        mygroup.addLayer(layer)
        
        ## 8.2. Raster
        rlayer = QgsRasterLayer(out10, 'Raster')
        rprovider = rlayer.dataProvider()
        colDic = {'f':'#fff5eb','f1': '#fee6ce', 'f2': '#fdd0a2', 'f3':'#fdae6b' , 'f4':'#fd8d3c', 'f5':'#f16913', 'f6':'#d94801','f7':'#a63603', 'f8':'#7f2704' }
        valueList = [0, 0.001, 10, 20, 30, 40, 50, 100, 500]
        lst = [QgsColorRampShader.ColorRampItem(valueList[0], QColor(colDic['f'])),
            QgsColorRampShader.ColorRampItem(valueList[1], QColor(colDic['f1'])),
            QgsColorRampShader.ColorRampItem(valueList[2], QColor(colDic['f2'])),
            QgsColorRampShader.ColorRampItem(valueList[3], QColor(colDic['f3'])),
            QgsColorRampShader.ColorRampItem(valueList[4], QColor(colDic['f4'])),
            QgsColorRampShader.ColorRampItem(valueList[5], QColor(colDic['f5'])),
            QgsColorRampShader.ColorRampItem(valueList[6], QColor(colDic['f6'])),
            QgsColorRampShader.ColorRampItem(valueList[7], QColor(colDic['f7'])),
            QgsColorRampShader.ColorRampItem(valueList[8], QColor(colDic['f8']))]
        my_shader = QgsRasterShader()
        my_colorramp = QgsColorRampShader()
        #fcn = QgsColorRampShader()
        #fcn.setColorRampType(QgsColorRampShader.Interpolated)
        #lst = [ QgsColorRampShader.ColorRampItem(0, QColor(0,255,0)),QgsColorRampShader.ColorRampItem(255, QColor(255,255,0)) ]
        my_colorramp.setColorRampItemList(lst)
        my_colorramp.setColorRampType(QgsColorRampShader.Interpolated)
        my_shader.setRasterShaderFunction(my_colorramp)
        renderer = QgsSingleBandPseudoColorRenderer(rlayer.dataProvider(), 1, my_shader)
        
        rasterTransparency = QgsRasterTransparency()
        myTransparentSingleValuePixelList = []
        myTransparentPixel1 = QgsRasterTransparency.TransparentSingleValuePixel()
        myTransparentPixel2 = QgsRasterTransparency.TransparentSingleValuePixel()
        
        myTransparentPixel1.min = 0
        myTransparentPixel1.max = 0.001
        myTransparentPixel1.percentTransparent = 100
        myTransparentSingleValuePixelList.append(myTransparentPixel1)

        myTransparentPixel2.min = 0.001
        myTransparentPixel2.max = 1000
        myTransparentPixel2.percentTransparent = 30
        myTransparentSingleValuePixelList.append(myTransparentPixel2)
        
        rasterTransparency.setTransparentSingleValuePixelList(myTransparentSingleValuePixelList)
        renderer.setRasterTransparency(rasterTransparency)
        
        rlayer.setRenderer(renderer)
        rlayer.triggerRepaint()
        QgsProject.instance().addMapLayer(rlayer)
        mygroup.addLayer(rlayer)
        
        
        
        outputs['LastStep'] = out9
        results['Tool done'] = outputs['LastStep']
        return results



