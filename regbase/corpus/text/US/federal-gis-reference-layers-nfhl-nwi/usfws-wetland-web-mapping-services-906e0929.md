---
source_id: federal-gis-reference-layers-nfhl-nwi
jurisdiction: US — FEMA (NFHL); U.S. Fish and Wildlife Service (NWI)
state: US
agency: FEMA (NFHL); U.S. Fish and Wildlife Service (NWI)
title: USFWS Wetland Web Mapping Services
doc_type: guidance
url: "https://www.fws.gov/program/national-wetlands-inventory/web-mapping-services"
sha256: f6ccc3cb3b85ddce53faf273c31f5ef074e5820912040d92689b6672bc3010f0
fetched_at: "2026-09-05T05:11:19+00:00"
---

<!-- heading-path: Wetland Web Mapping Services -->
## Wetland Web Mapping Services
National Wetland Inventory (NWI) geospatial wetlands data and reference layers can be accessed by web-based applications and mapping software using the following Open GIS Consortium (OGC) compliant web mapping services. These services allow GIS users to display and query wetlands data without the overhead of data management. Additionally, web developers can consume these services to include NWI wetland data into their own mapping applications. These services are updated biannually along with the Wetlands Mapper.

<!-- heading-path: Wetland Web Mapping Services > Representational State Transfer (REST) -->
## Representational State Transfer (REST)
Software developers can incorporate our REST services within their map applications using the link provided. GIS users can connect to these services using mapping software such as ESRI's ArcGIS by following the directions provided.
REST Service address : https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest

<!-- heading-path: Wetland Web Mapping Services > Representational State Transfer (REST) > Connecting to the Wetlands REST services in ESRI' ArcGIS -->
### Connecting to the Wetlands REST services in ESRI' ArcGIS
Launch ArcPro.
In the 'Contents' window, right click and select New -> New Server -> New ArcGIS Server.
Enter the following REST address in the Server URL box: https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest
Click 'OK'.
Click Finish.
In ArcPro under Servers, double click on 'wetlandsmapservice on fwspublicservices.wim.usgs.gov.ags'
Select the layers you would like to add to ArcPro.

<!-- heading-path: Wetland Web Mapping Services > Web Map Services (WMS) -->
## Web Map Services (WMS)
Software developers can incorporate our WMS services within their applications using the service information and links provided. GIS users can connect to these services using mapping software such as ESRI's ArcGIS by following the directions provided.
WMS Service Name : Wetlands
Projection : GCS, NAD83
OGC Version : 1.3
Wetlands Data* : https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Wetl…
Data Source: https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Data… ?
Wetlands Raster* : https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Wetl…
Wetlands Status : https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Wetl…
Riparian Data : https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Ripa…

<!-- heading-path: Wetland Web Mapping Services > Web Map Services (WMS) > Connecting to the Wetlands WMS in ESRI' ArcGIS -->
### Connecting to the Wetlands WMS in ESRI' ArcGIS
Launch ArcPro.
In the 'Contents' window, right click and select New -> New Server -> New WMS Server.
Enter the following WMS address in the URL text box: Wetlands Data WMS address: https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Wetl… ; Data Source WMS address: https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Data… ; Wetlands Raster WMS address: https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Wetl… ; Wetlands Status WMS address: https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Wetl… ; Riparian Data WMS address: https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Ripa… ;
Enter the following WMS address in the URL text box:
Wetlands Data WMS address: https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Wetl… ; Data Source WMS address: https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Data… ; Wetlands Raster WMS address: https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Wetl… ; Wetlands Status WMS address: https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Wetl… ; Riparian Data WMS address: https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/services/Ripa… ;
Click on the “Get Layers” button to view the service and layer information.
