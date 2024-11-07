import logging

logger = logging.getLogger(__name__)

DATASET_MAPPING = {
    "EO:CLMS:DAT:CGLS_DAILY10_LST_DC_GLOBAL_V1": "EO:CLMS:DAT:CLMS_GLOBAL_LST_5KM_V1_10DAILY-DAILY-CYCLE_NETCDF",
    "EO:CLMS:DAT:CGLS_DAILY10_LST_DC_GLOBAL_V2": "EO:CLMS:DAT:CLMS_GLOBAL_LST_5KM_V2_10DAILY-DAILY-CYCLE_NETCDF",
    "EO:CLMS:DAT:CGLS_DAILY10_LST_TCI_GLOBAL_V1": "EO:CLMS:DAT:CLMS_GLOBAL_LST_5KM_V1_10DAILY-TCI_NETCDF",
    "EO:CLMS:DAT:CGLS_DAILY10_LST_TCI_GLOBAL_V2": "EO:CLMS:DAT:CLMS_GLOBAL_LST_5KM_V2_10DAILY-TCI_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_ALBH_V1_1KM": "EO:CLMS:DAT:CLMS_GLOBAL_ALBH_1KM_V1_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_ALDH_V1_1KM": "EO:CLMS:DAT:CLMS_GLOBAL_ALDH_1KM_V1_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_DMP300_V1_333M": "EO:CLMS:DAT:CLMS_GLOBAL_DMP_300M_V1_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_DMP_V2_1KM": "EO:CLMS:DAT:CLMS_GLOBAL_DMP_1KM_V2_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_FAPAR300_V1_333M": "EO:CLMS:DAT:CLMS_GLOBAL_FAPAR_300M_V1_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_FAPAR_V1_1KM": "EO:CLMS:DAT:CLMS_GLOBAL_FAPAR_1KM_V1_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_FAPAR_V2_1KM": "EO:CLMS:DAT:CLMS_GLOBAL_FAPAR_1KM_V2_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_FCOVER300_V1_333M": "EO:CLMS:DAT:CLMS_GLOBAL_FCOVER_300M_V1_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_FCOVER_V1_1KM": "EO:CLMS:DAT:CLMS_GLOBAL_FCOVER_1KM_V1_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_FCOVER_V2_1KM": "EO:CLMS:DAT:CLMS_GLOBAL_FCOVER_1KM_V2_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_GDMP300_V1_333M": "EO:CLMS:DAT:CLMS_GLOBAL_GDMP_300M_V1_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_GDMP_V2_1KM": "EO:CLMS:DAT:CLMS_GLOBAL_GDMP_1KM_V2_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_LAI300_V1_333M": "EO:CLMS:DAT:CLMS_GLOBAL_LAI_300M_V1_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_LAI_V1_1KM": "EO:CLMS:DAT:CLMS_GLOBAL_LAI_1KM_V1_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_LAI_V2_1KM": "EO:CLMS:DAT:CLMS_GLOBAL_LAI_1KM_V2_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_NDVI300_V1_333M": "EO:CLMS:DAT:CLMS_GLOBAL_NDVI_300M_V1_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_NDVI300_V2_333M": "EO:CLMS:DAT:CLMS_GLOBAL_NDVI_300M_V2_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_NDVI_V2_1KM": "EO:CLMS:DAT:CLMS_GLOBAL_NDVI_1KM_V2_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_NDVI_V3_1KM": "EO:CLMS:DAT:CLMS_GLOBAL_NDVI_1KM_V3_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_GLOBAL_SWI10_V3_0.1DEGREE": "EO:CLMS:DAT:CLMS_GLOBAL_SWI_12.5KM_V3_10DAILY_NETCDF",
    "EO:CLMS:DAT:CGLS_HOURLY_LST_GLOBAL_V1": "EO:CLMS:DAT:CLMS_GLOBAL_LST_5KM_V1_HOURLY_NETCDF",
    "EO:CLMS:DAT:CGLS_HOURLY_LST_GLOBAL_V2": "EO:CLMS:DAT:CLMS_GLOBAL_LST_5KM_V2_HOURLY_NETCDF",
    "EO:EEA:DAT:VEGETATION_DAILY_SWI_12.5KM_GLOBAL_V3": "EO:CLMS:DAT:CLMS_GLOBAL_SWI_12.5KM_V3_DAILY_NETCDF",
    "EO:EEA:DAT:VEGETATION:DAILY_SWI_1KM_EUROPE_V1": "EO:CLMS:DAT:CLMS_GLOBAL_SWI_1KM_V1_DAILY_NETCDF",
    "EO:EEA:DAT:ENERGY_TOCR_1KM_GLOBAL_V1": "EO:CLMS:DAT:CLMS_GLOBAL_TOCR_1KM_V1_10DAILY_NETCDF",
    "EO:EEA:DAT:VEGETATION:DAILY_SWI_12.5KM_GLOBAL_V3": "EO:CLMS:DAT:CLMS_GLOBAL_SSM_1KM_V1_DAILY_NETCDF",
    "EO:ESA:DAT:SENTINEL-1:SAR": "EO:ESA:DAT:SENTINEL-1",
    "EO:ESA:DAT:SENTINEL-2:MSI": "EO:ESA:DAT:SENTINEL-2",
}


def convert(query):
    """Converts a query in HDA v1 format into an HDA v2 one.
    Might not work in every case.
    If a v2 query is passed in, it is returned as is."""
    dataset_id = query.get("datasetId")

    if dataset_id is None and "dataset_id" in query:
        return query

    logger.warning(
        "The submitted query is still in HDA v1 format. "
        "It will be automatically converted, if possible, "
        "but it is recommended to update it manually."
    )

    # Modify the JSON query according to the new structure
    dataset_id = DATASET_MAPPING.get(dataset_id, dataset_id)
    new_query = {"dataset_id": dataset_id}

    # Check if the original JSON has the "dateRangeSelectValues" field
    if "dateRangeSelectValues" in query:
        # Loop through the dateRangeSelectValues and add fields to new_query
        for date_range_value in query["dateRangeSelectValues"]:
            name = date_range_value["name"].lower()
            start = date_range_value["start"]
            end = date_range_value["end"]

            if dataset_id.startswith("EO:ECMWF:DAT:CAMS_"):
                new_query["dtstart"] = start
                new_query["dtend"] = end
            elif dataset_id.startswith("EO:CLMS:DAT:"):
                new_query["start"] = start
                new_query["end"] = end
            elif dataset_id.startswith("EO:MO:DAT:"):
                new_query["min_date"] = start
                new_query["max_date"] = end
            elif dataset_id.startswith("EO:EUM:DAT:"):
                new_query["dtstart"] = start
                new_query["dtend"] = end
            elif dataset_id.startswith("EO:EEA:DAT:CLMS_HRVPP"):
                new_query["start"] = start
                new_query["end"] = end
            elif dataset_id.startswith("EO:CNES:DAT:SWH"):
                new_query["creationDateStart"] = start
                new_query["creationDateEnd"] = end
            elif dataset_id.startswith("EO:ESA"):
                new_query["startDate"] = start
                new_query["completionDate"] = end
            else:
                new_query[f"{name}_start"] = start
                new_query[f"{name}_end"] = end

    if "boundingBoxValues" in query:
        new_query["bbox"] = query["boundingBoxValues"][0]["bbox"]

    # Add a "test" field for stringInputValues
    if "stringInputValues" in query:
        # Loop through the stringInputValues and add fields to new_query
        for string_input_value in query["stringInputValues"]:
            name = string_input_value["name"]
            value = string_input_value["value"]
            new_query[name] = value

    # Add a "test" field for stringChoiceValues
    if "stringChoiceValues" in query:
        # Loop through the stringChoiceValues and add fields to new_query
        for string_choice_value in query["stringChoiceValues"]:
            name = string_choice_value["name"]
            value = string_choice_value["value"]
            new_query[name] = value

    # Add a "test" field for multiStringSelectValues
    if "multiStringSelectValues" in query:
        # Loop through the stringChoiceValues and add fields to new_query
        for multi_string_select_value in query["multiStringSelectValues"]:
            name = multi_string_select_value["name"]
            value = multi_string_select_value["value"]
            new_query[name] = value

    return new_query
