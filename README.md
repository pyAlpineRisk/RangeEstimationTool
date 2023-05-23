# Range-Estimation-Tool
In the specific example of estimating range using a flat-rate slope approach, a rough delineation of the range of landslide processes is calculated using Python and QGIS, incorporating GIS and terrain analyses.

 <h2>Case Examples</h2>
 <p>
<i lang="id">Input Parameters:</i>
 
 ![image](https://github.com/pyAlpineRisk/RangeEstimationTool/assets/52344347/817db708-2c8b-4103-8beb-d673ee12a2b8)

 <p> The data basis or input parameters consist, on the one hand, of the Digital Elevation Model (DEM) based on airborne laser scanning data with a resolution of 1 meter, and on the other hand, the query line (break line; shape line) in vector format. Additionally, either the predetermined fixed gradient of 30° can be chosen or this value can be determined manually.</p> 



<h2>Installation/Application</h2>
<p>The scripts are written for PyQGIS 3.16 and can be used by installing QGIS 3.16 or above.

To install QGIS tools developed for QGIS 3.x, copy them into
~/AppData/Roaming/QGIS/QGIS3/profiles/default/processing/scripts or in the upper part of the toolbox dialog you can add the scripts with ![mIconPythonFile](https://user-images.githubusercontent.com/52344347/136413201-b4a1f7d3-4053-4aa6-b11c-9433ae617057.png) Scripts - Add Script to Toolbox ...

After that the tools can be found in the QGIS "Processing Toolbox" - Scripts</p>
